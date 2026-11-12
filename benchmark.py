#!/usr/bin/env python3
"""
Benchmark harness for the Olist SQL-efficiency study.

Timing method
-------------
MariaDB does not implement MySQL's EXPLAIN ANALYZE, so elapsed time is taken
from the server's own statement profiler (`SET profiling=1` ... `SHOW
PROFILES`). Server-side profiling is preferable to client-side wall-clock
timing here because it excludes client transport and result-set formatting,
which are not part of what we are trying to measure.

Every measurement is repeated REPEATS times after WARMUP untimed executions.
The median is reported as the primary statistic (robust to scheduler noise on a
shared machine); mean, standard deviation, min and max are also recorded.

Plan inspection
---------------
`EXPLAIN` gives the chosen plan; `ANALYZE <query> FORMAT=JSON` gives the
*actual* row counts per plan node, which is how "rows examined vs. rows
returned" ratios are computed.

Outputs results.json / results.csv in the results directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time

SOCK = os.environ.get("MYSQL_SOCK", "/tmp/opencode/mysql/run/my.sock")
WARMUP = 3
REPEATS = 30
# Hard ceiling on any single statement. Without this a pathological plan (for
# example an unindexed anti-join that degrades to a cartesian product) can hang
# the whole sweep instead of being recorded as a censored measurement.
MAX_STATEMENT_SECONDS = 45

# --------------------------------------------------------------------------
# Index configurations (phases).
#
# Every configuration is rebuilt from scratch so that configurations are
# directly comparable rather than cumulative. "reset_fk=True" restores the
# schema to its post-import state: primary keys plus the secondary indexes that
# MySQL/MariaDB create implicitly to enforce foreign keys. That post-import
# state is itself a realistic and interesting control - it is what an analyst
# gets from a naive CSV import with declared referential integrity.
#
# "reset_zero=True" additionally drops the foreign keys, yielding a schema with
# no secondary index at all - the absolute sequential-scan floor.
# --------------------------------------------------------------------------
FK_DDL = [
    ("orders", "fk_orders_customer",
     "FOREIGN KEY (customer_id) REFERENCES customers(customer_id)"),
    ("order_items", "fk_items_order",
     "FOREIGN KEY (order_id) REFERENCES orders(order_id)"),
    ("order_items", "fk_items_product",
     "FOREIGN KEY (product_id) REFERENCES products(product_id)"),
    ("order_items", "fk_items_seller",
     "FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)"),
    ("order_payments", "fk_pay_order",
     "FOREIGN KEY (order_id) REFERENCES orders(order_id)"),
]

PHASES = [
    {
        "id": "C0_zero",
        "label": "C0 - no secondary index (sequential-scan floor)",
        "reset": "zero",
        "ddl": [],
    },
    {
        "id": "C1_fk",
        "label": "C1 - foreign-key indexes only (post-import baseline)",
        "reset": "fk",
        "ddl": [],
    },
    {
        "id": "C2_single",
        "label": "C2 - FK + single-column indexes",
        "reset": "fk",
        "ddl": [
            "CREATE INDEX ix_orders_status ON orders(order_status)",
            "CREATE INDEX ix_orders_purch_ts ON orders(order_purchase_timestamp)",
            "CREATE INDEX ix_customers_state ON customers(customer_state)",
            "CREATE INDEX ix_customers_zip ON customers(customer_zip_code_prefix)",
            "CREATE INDEX ix_items_seller ON order_items(seller_id)",
            "CREATE INDEX ix_items_product ON order_items(product_id)",
            "CREATE INDEX ix_sellers_state ON sellers(seller_state)",
            "CREATE INDEX ix_products_cat ON products(product_category_name)",
            "CREATE INDEX ix_payments_type ON order_payments(payment_type)",
            "CREATE INDEX ix_reviews_score ON order_reviews(review_score)",
        ],
    },
    {
        "id": "C3_composite",
        "label": "C3 - FK + composite indexes (equality, range)",
        "reset": "fk",
        "ddl": [
            "CREATE INDEX ix_orders_status_ts ON orders(order_status, order_purchase_timestamp)",
            "CREATE INDEX ix_orders_cust_ts ON orders(customer_id, order_purchase_timestamp)",
            "CREATE INDEX ix_customers_state_zip ON customers(customer_state, customer_zip_code_prefix)",
            "CREATE INDEX ix_items_seller_price ON order_items(seller_id, price)",
        ],
    },
    {
        "id": "C4_covering",
        "label": "C4 - FK + composite + covering indexes",
        "reset": "fk",
        "ddl": [
            "CREATE INDEX ix_orders_status_ts ON orders(order_status, order_purchase_timestamp)",
            "CREATE INDEX ix_orders_cov ON orders(order_status, order_purchase_timestamp, customer_id)",
            "CREATE INDEX ix_customers_cov ON customers(customer_state, customer_zip_code_prefix, customer_id)",
            "CREATE INDEX ix_items_seller_price ON order_items(seller_id, price)",
            # Index on the anti-join probe column. Without it the LEFT JOIN
            # formulation of W5 has no usable access path in any configuration,
            # so the family would never converge and the effect of the join
            # column index could not be observed.
            "CREATE INDEX ix_reviews_order_score ON order_reviews(order_id, review_score)",
        ],
    },
]


# --------------------------------------------------------------------------
# Query workloads
# --------------------------------------------------------------------------
def q(label, group, sql, note="", expects_rows=True):
    return {"label": label, "group": group, "sql": sql.strip(), "note": note,
            "expects_rows": expects_rows}


# Driving predicate for the W5 anti-join family.
#
# A 14-day purchase window keeps the family measurable. Two design decisions
# matter here:
#   * The date restriction is expressed as a top-level WHERE predicate on
#     `orders` rather than wrapped in a derived table. With derived_merge on
#     (the default) the derived table is folded into the outer query, which
#     turns the LEFT JOIN variant into a full cartesian product and makes it
#     unmeasurable.
#   * All three variants share the identical driving relation, so the
#     comparison isolates join *formulation* rather than input size.
W5_WINDOW = ("o.order_purchase_timestamp >= '2018-06-01 00:00:00' "
             "AND o.order_purchase_timestamp <  '2018-06-15 00:00:00'")

QUERIES = [
    # ---- W1: single-table filter and aggregation -------------------------
    q("W1.1", "W1 single-table filter",
      "SELECT COUNT(*) AS n FROM orders WHERE order_status = 'delivered'",
      "Point predicate on a low-cardinality column"),
    q("W1.2", "W1 single-table filter",
      """SELECT order_status, COUNT(*) AS n, ROUND(SUM(pay),2) AS revenue
         FROM (SELECT order_status,
                      (SELECT SUM(p.payment_value) FROM order_payments p
                        WHERE p.order_id = o.order_id) AS pay
                 FROM orders o) t
         GROUP BY order_status ORDER BY n DESC""",
      "Correlated payment roll-up grouped by status"),
    q("W1.3", "W1 single-table filter",
      "SELECT customer_state, COUNT(*) AS n FROM customers GROUP BY customer_state ORDER BY n DESC",
      "Grouped count, fully covered by customers.customer_state"),

    # ---- W2: SARGability -------------------------------------------------
    # Two predicate pairs. Each pair returns identical row counts and differs
    # only in whether a function is applied to the filtered column, so the
    # difference isolates predicate form.
    #
    # The month pair is deliberately *selective* (~3% of orders) and the year
    # pair is deliberately *non-selective* (~59% of orders). SARGability can only
    # pay off when it lets the server avoid reading rows, so selectivity is the
    # moderating variable and both regimes are needed to show it.
    q("W2.1 non-SARG month", "W2 SARGability (selective)",
      "SELECT COUNT(*) AS n FROM orders "
      "WHERE DATE_FORMAT(order_purchase_timestamp,'%Y-%m') = '2018-06'",
      "Function on the column, selective month (non-SARGable)"),
    q("W2.2 SARG month", "W2 SARGability (selective)",
      """SELECT COUNT(*) AS n FROM orders
         WHERE order_purchase_timestamp >= '2018-06-01 00:00:00'
           AND order_purchase_timestamp <  '2018-07-01 00:00:00'""",
      "Half-open range on the column, selective month (SARGable)"),
    q("W2.3 non-SARG year", "W2 SARGability (non-selective)",
      "SELECT COUNT(*) AS n FROM orders WHERE YEAR(order_purchase_timestamp) = 2018",
      "Function on the column, whole year (non-SARGable)"),
    q("W2.4 SARG year", "W2 SARGability (non-selective)",
      """SELECT COUNT(*) AS n FROM orders
         WHERE order_purchase_timestamp >= '2018-01-01 00:00:00'
           AND order_purchase_timestamp <  '2019-01-01 00:00:00'""",
      "Half-open range on the column, whole year (SARGable)"),

    # ---- W3: two-table inner join ---------------------------------------
    q("W3.1", "W3 two-table INNER JOIN",
      """SELECT c.customer_state, COUNT(*) AS n_orders
         FROM orders o
         JOIN customers c ON c.customer_id = o.customer_id
         WHERE o.order_status = 'delivered'
         GROUP BY c.customer_state
         ORDER BY n_orders DESC""",
      "Equi-join on customer_id, grouped by customer_state"),

    # ---- W4: semi-join equivalence: JOIN vs IN vs EXISTS -----------------
    q("W4.1 JOIN", "W4 semi-join (JOIN/IN/EXISTS)",
      """SELECT COUNT(*) AS n FROM orders o
         JOIN customers c ON c.customer_id = o.customer_id
         WHERE c.customer_state = 'SP'""",
      "INNER JOIN form of the semi-join"),
    q("W4.2 IN", "W4 semi-join (JOIN/IN/EXISTS)",
      """SELECT COUNT(*) AS n FROM orders o
         WHERE o.customer_id IN (
           SELECT c.customer_id FROM customers c WHERE c.customer_state = 'SP')""",
      "Uncorrelated IN subquery (semi-join candidate)"),
    q("W4.3 EXISTS", "W4 semi-join (JOIN/IN/EXISTS)",
      """SELECT COUNT(*) AS n FROM orders o
         WHERE EXISTS (SELECT 1 FROM customers c
                        WHERE c.customer_id = o.customer_id
                          AND c.customer_state = 'SP')""",
      "Correlated EXISTS subquery"),

# ---- W5: anti-join equivalence: LEFT JOIN vs NOT IN vs NOT EXISTS ----
    q("W5.1 LEFT JOIN", "W5 anti-join (LEFT JOIN/NOT IN/NOT EXISTS)",
      f"""SELECT COUNT(*) AS n FROM orders o
         LEFT JOIN order_reviews r
                ON r.order_id = o.order_id AND r.review_score = 5
         WHERE {W5_WINDOW}
           AND r.order_id IS NULL""",
      "LEFT JOIN ... IS NULL anti-join form"),
    q("W5.2 NOT IN", "W5 anti-join (LEFT JOIN/NOT IN/NOT EXISTS)",
      f"""SELECT COUNT(*) AS n FROM orders o
         WHERE {W5_WINDOW}
           AND o.order_id NOT IN (
             SELECT r.order_id FROM order_reviews r WHERE r.review_score = 5)""",
      "Uncorrelated NOT IN anti-join form"),
    q("W5.3 NOT EXISTS", "W5 anti-join (LEFT JOIN/NOT IN/NOT EXISTS)",
      f"""SELECT COUNT(*) AS n FROM orders o
         WHERE {W5_WINDOW}
           AND NOT EXISTS (SELECT 1 FROM order_reviews r
                            WHERE r.order_id = o.order_id AND r.review_score = 5)""",
      "Correlated NOT EXISTS anti-join form"),

    # ---- W6: multi-table analytical aggregation --------------------------
    q("W6.1 flat JOIN", "W6 4-table analytical aggregation",
      """SELECT c.customer_state,
               DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') AS ym,
               ROUND(SUM(i.price),2) AS gmv,
               COUNT(DISTINCT o.order_id) AS orders
         FROM orders o
         JOIN customers c ON c.customer_id = o.customer_id
         JOIN order_items i ON i.order_id = o.order_id
         WHERE o.order_status <> 'canceled'
         GROUP BY c.customer_state, ym
         ORDER BY gmv DESC""",
      "Flat 4-table join, month x state revenue"),
    q("W6.2 derived table", "W6 4-table analytical aggregation",
      """SELECT t.customer_state, t.ym, ROUND(SUM(t.price),2) AS gmv,
               COUNT(DISTINCT t.order_id) AS orders
         FROM (
           SELECT c.customer_state,
                  o.customer_id,
                  DATE_FORMAT(o.order_purchase_timestamp,'%Y-%m') AS ym,
                  i.price, o.order_id
           FROM orders o
           JOIN customers c ON c.customer_id = o.customer_id
           JOIN order_items i ON i.order_id = o.order_id
           WHERE o.order_status <> 'canceled'
         ) t
         GROUP BY t.customer_state, t.ym
         ORDER BY gmv DESC""",
      "Join hoisted into a derived table (materialisation variant)"),

    # ---- W7: window function ---------------------------------------------
    q("W7.1", "W7 window function ranking",
      """SELECT seller_id, state, revenue, rnk FROM (
         SELECT i.seller_id, s.seller_state AS state,
                SUM(i.price) AS revenue,
                RANK() OVER (PARTITION BY s.seller_state
                             ORDER BY SUM(i.price) DESC) AS rnk
         FROM order_items i
         JOIN sellers s ON s.seller_id = i.seller_id
         GROUP BY i.seller_id, s.seller_state) t
       WHERE rnk <= 3
       ORDER BY state, rnk""",
      "Top-3 sellers per state via RANK() window function"),

    # ---- W8: top-N with ORDER BY + LIMIT --------------------------------
    q("W8.1", "W8 ORDER BY + LIMIT",
      """SELECT o.order_id, o.order_purchase_timestamp, c.customer_city, c.customer_state
         FROM orders o
         JOIN customers c ON c.customer_id = o.customer_id
         ORDER BY o.order_purchase_timestamp DESC
         LIMIT 20""",
      "Newest 20 orders - needs a sort unless an index supplies the order"),
]


# --------------------------------------------------------------------------
# mysql client plumbing
# --------------------------------------------------------------------------
def run_sql(sql: str, db: str = "olist_bp", raw: bool = False):
    cmd = ["mariadb", f"--socket={SOCK}", "-u", "root", "-N", "-B", db, "-e", sql]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"SQL failed: {proc.stderr.strip()}\n--- sql ---\n{sql[:400]}")
    return proc.stdout if raw else proc.stdout.strip()


def _sec_indexes() -> list[tuple[str, str]]:
    out = run_sql(
        "SELECT TABLE_NAME, INDEX_NAME FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA='olist_bp' AND INDEX_NAME <> 'PRIMARY' "
        "GROUP BY TABLE_NAME, INDEX_NAME;")
    rows = []
    for line in out.splitlines():
        if line.strip():
            table, index = line.split("\t")
            rows.append((table, index))
    return rows


def reset_schema(mode: str) -> None:
    """Rebuild the schema to the requested secondary-index baseline."""
    # drop foreign keys first so their implicit indexes can be removed
    for table, name, _ in FK_DDL:
        try:
            run_sql(f"ALTER TABLE {table} DROP FOREIGN KEY {name}")
        except RuntimeError:
            pass
    for table, index in _sec_indexes():
        try:
            run_sql(f"ALTER TABLE {table} DROP INDEX {index}")
        except RuntimeError:
            pass
    if mode == "fk":
        for table, name, ddl in FK_DDL:
            run_sql(f"ALTER TABLE {table} ADD CONSTRAINT {name} {ddl}")
    elif mode != "zero":
        raise ValueError(mode)


def apply_phase(phase: dict) -> None:
    reset_schema(phase["reset"])
    for ddl in phase["ddl"]:
        try:
            run_sql(ddl)
        except RuntimeError as exc:
            if "Duplicate key name" not in str(exc):
                raise
    run_sql("ANALYZE TABLE orders, order_items, customers, sellers, "
            "products, order_payments, order_reviews;")


def timed_once(sql: str) -> tuple[float, int, int]:
    """Run one statement under the server profiler.

    Returns (duration_seconds, rows_returned, result_set_bytes).
    """
    body = sql.rstrip().rstrip(";")
    script = (f"SET profiling=1;\n"
              f"SET STATEMENT max_statement_time={MAX_STATEMENT_SECONDS} FOR\n"
              f"{body};\n"
              f"SHOW PROFILES;")
    out = run_sql(script, raw=True)
    lines = [l for l in out.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        raise RuntimeError(f"no profile row for: {sql[:120]}\n{out[:400]}")
    # SHOW PROFILES prints one row per profiled statement; take the last one,
    # which is the measured query (the SETs are not profiled).
    prof = None
    for line in reversed(lines):
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                prof = (float(parts[1]), int(parts[0]))
                break
            except ValueError:
                continue
    if prof is None:
        raise RuntimeError(f"unparsable profile output: {out[:400]}")
    if prof[0] >= MAX_STATEMENT_SECONDS - 0.5:
        raise TimeoutError(
            f"statement exceeded max_statement_time={MAX_STATEMENT_SECONDS}s")
    return prof[0], prof[1], len(out)


def measure(query: dict, repeats: int, warmup: int) -> dict:
    for _ in range(warmup):
        timed_once(query["sql"])

    durations, rows = [], None
    for _ in range(repeats):
        d, r, _ = timed_once(query["sql"])
        durations.append(d)
        rows = r

    return {
        "runs": repeats,
        "rows_returned": rows,
        "mean_ms": statistics.mean(durations) * 1000,
        "median_ms": statistics.median(durations) * 1000,
        "stdev_ms": (statistics.stdev(durations) * 1000) if len(durations) > 1 else 0.0,
        "min_ms": min(durations) * 1000,
        "max_ms": max(durations) * 1000,
        "raw_ms": [round(d * 1000, 4) for d in durations],
    }


def explain(query: dict) -> dict:
    plan = run_sql(f"EXPLAIN {query['sql']}")
    rows_examined = None
    try:
        ajson = run_sql(f"ANALYZE FORMAT=JSON {query['sql']}", raw=True)
        m = re.search(r'"r_rows_lo_p"?:?\s*(\d+)', ajson)
        rows_examined = int(m.group(1)) if m else None
    except RuntimeError:
        pass
    return {"explain": plan, "rows_examined_estimate": rows_examined}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "results"))
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--warmup", type=int, default=WARMUP)
    ap.add_argument("--phases", default="", help="comma-separated phase ids")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    phases = PHASES
    if args.phases:
        want = {p.strip() for p in args.phases.split(",")}
        phases = [p for p in PHASES if p["id"] in want]

    results = []
    t0 = time.time()
    for phase in phases:
        print(f"\n=== phase {phase['id']}: {phase['label']} ===", flush=True)
        apply_phase(phase)
        idx = run_sql(
            "SELECT TABLE_NAME, INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) "
            "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='olist_bp' "
            "AND INDEX_NAME <> 'PRIMARY' GROUP BY TABLE_NAME, INDEX_NAME;")
        print("  secondary indexes:", len(idx.splitlines()) if idx else 0)

        for query in QUERIES:
            label = f"{query['label']}"
            print(f"  [{label:>16s}] {query['group'][:34]:34s} ...", end="", flush=True)
            try:
                m = measure(query, args.repeats, args.warmup)
                e = explain(query)
                rec = {"phase": phase["id"], "phase_label": phase["label"],
                       **query, **m, **e}
                results.append(rec)
                print(f" median={m['median_ms']:9.3f} ms  rows={m['rows_returned']}")
            except TimeoutError as exc:
                print(f" CENSORED (>={MAX_STATEMENT_SECONDS}s)")
                results.append({"phase": phase["id"], "phase_label": phase["label"],
                                **query, "error": "timeout",
                                "median_ms": MAX_STATEMENT_SECONDS * 1000.0,
                                "censored": True})
            except RuntimeError as exc:
                print(f" ERROR {str(exc)[:120]}")
                results.append({"phase": phase["id"], "phase_label": phase["label"],
                                **query, "error": str(exc)})

    out_json = os.path.join(args.out, "results.json")
    with open(out_json, "w") as fh:
        json.dump({"warmup": args.warmup, "repeats": args.repeats,
                   "socket": SOCK, "results": results}, fh, indent=2)

    with open(os.path.join(args.out, "results.csv"), "w") as fh:
        cols = ["phase", "label", "group", "median_ms", "mean_ms", "stdev_ms",
                "min_ms", "max_ms", "rows_returned", "rows_examined_estimate"]
        fh.write(",".join(cols) + "\n")
        for r in results:
            if "error" in r:
                continue
            fh.write(",".join(str(r.get(c, "")) for c in cols) + "\n")

    print(f"\nwrote {out_json}  ({len(results)} records, {time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())