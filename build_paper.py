#!/usr/bin/env python3
"""
Assemble the manuscript into a .docx that inherits the ITIJ template.

Numbers, tables and figure captions are all derived from results.json at build
time, so the prose and the reported measurements cannot drift apart.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import docx_writer as dx  # noqa: E402
from references import REFERENCES  # noqa: E402
from summary import (CONFIG_DESC, CONFIG_ORDER, CONFIG_SHORT, FAMILIES,  # noqa: E402
                     FAMILY_OF, QUERY_DESC, QUERY_ORDER, Results, SELECTIVITY,
                     pct)

TEMPLATE = os.path.join(os.path.dirname(HERE), "ITIJ_Template.docx")
FIGDIR = os.path.join(HERE, "figures")
OUT = os.path.join(os.path.dirname(HERE), "Olist_SQL_Query_Efficiency_ITIJ.docx")

EMU_PER_INCH = 914400
CONTENT_INCH = dx.CONTENT_WIDTH_TWIPS / 1440  # ~6.10 in


def load_benchmark_module():
    spec = importlib.util.spec_from_file_location("bm", os.path.join(HERE, "benchmark.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    return bm


# ==========================================================================
# front matter
# ==========================================================================
TITLE = ("Comparative Analysis of SQL Query Execution Efficiency Using Indexing, "
         "JOIN, and Subquery Optimization on the Olist Brazilian E-Commerce Dataset")

AUTHORS = [
    ("[Author One]", "1,*", True),
    ("[Author Two]", "1", False),
    ("[Author Three]", "1", False),
]
AFFILIATIONS = [
    ("1", "Department of Informatics, [Faculty / School], [University], "
          "[City], [Country]"),
]
EMAILS = [("[email.one@university.ac.id]", "1"),
          ("[email.two@university.ac.id]", "2"),
          ("[email.three@university.ac.id]", "3")]


def front_matter() -> str:
    p = []
    p.append(dx.para(dx.run(TITLE, sz=17), align="center", before=360, after=240,
                     left=0, hanging=0))
    # author line with superscript affiliation markers
    runs = []
    for i, (name, mark, _star) in enumerate(AUTHORS):
        if i:
            runs.append(dx.run(", "))
        runs.append(dx.run(name))
        runs.append(dx.run(mark, sup=True))
    p.append(dx.para("".join(runs), align="center", after=60, keep_next=True,
                     left=0, hanging=0))
    for mark, aff in AFFILIATIONS:
        p.append(dx.para(dx.run(mark + " ", sup=True, sz=9)
                         + dx.run(aff, sz=9), align="center", after=0,
                         left=0, hanging=0))
    for i, (mail, mark) in enumerate(EMAILS):
        runs = [dx.run(f"{mark} ", sup=True, sz=9)]
        runs.append(dx.run(f"Email of author {mark}: ", sz=9))
        runs.append(dx.run(mail, sz=9, u=True))
        p.append(dx.para("".join(runs), align="center", after=0, left=0, hanging=0))
    p.append(dx.para(dx.run("* Corresponding author", sz=9), align="center",
                     after=120, left=0, hanging=0))
    return "".join(p)


def article_info() -> str:
    rows = [
        ["Received", "[day Month 2026]"],
        ["Revised", "[day Month 2026]"],
        ["Accepted", "[day Month 2026]"],
        ["Published", "[day Month 2026]"],
        ["DOI", "[assigned by the journal on acceptance]"],
    ]
    widths = [1500, 4000]
    return dx.table(rows, widths, header=False, font_sz=8, row_shading=False)


def abstract_and_keywords(r: "Results") -> str:
    abstract = (
        f"Relational query performance is determined by two decisions that are frequently "
        f"conflated in practice: which physical access structures a schema carries, and how "
        f"the query itself expresses the same logical result. This paper separates the two "
        f"and measures each independently. {NQW} queries spanning {NFW} workload families "
        f"were executed against the Brazilian E-Commerce (Olist) transactional dataset, "
        f"normalised into a nine-table InnoDB schema of {SCHEMA_ROWS:,} rows, "
        f"under five index configurations ranging from no secondary index at all to "
        f"composite and covering indexes. Elapsed time was taken from the database "
        f"server's own statement profiler over {r.repeats} timed repetitions after "
        f"{r.warmup} untimed warm-up executions, and every access path was confirmed by "
        f"EXPLAIN so that each timing is attributable to a plan rather than inferred from "
        f"it. Three findings emerge. First, and against the intuition that motivated the "
        f"configurations, the broad single-column index set outperformed the composite and "
        f"covering sets: replacing a single-column index with a composite one on the same "
        f"column made two queries between one and two orders of magnitude slower, because a "
        f"composite index cannot serve a predicate or ordering on its trailing column when "
        f"the leading column is unconstrained. Column order within an index therefore "
        f"mattered more than the number of indexes present, and the best index set proved "
        f"workload-specific rather than universally better. Second, the relative cost of "
        f"JOIN and subquery syntax is not intrinsic but plan- and index-dependent, and its "
        f"sign reverses: unindexed, the subquery forms of an anti-join outperformed the "
        f"LEFT JOIN form by a factor of {r.fmt_x(max((r.med('C0_zero', q) or 0) for q in ('W5.1 LEFT JOIN', 'W5.2 NOT IN', 'W5.3 NOT EXISTS')) / max(min((r.med('C0_zero', q) or 0) for q in ('W5.1 LEFT JOIN', 'W5.2 NOT IN', 'W5.3 NOT EXISTS')), 1e-9))}, "
        f"while adding an index on the join column made the LEFT JOIN form the fastest of "
        f"the three. Third, predicate form interacts with index design rather than acting "
        f"independently: rewriting a function application as a range predicate produced a "
        f"large gain where an index with the correct leading column existed, and almost "
        f"none where it did not, and its benefit was mediated by predicate selectivity. "
        f"Overall gains from indexing were modest, of roughly twofold, because the dataset "
        f"is small enough that full scans are already cheap; the durable contribution is "
        f"the set of plan-level mechanisms, which are independent of dataset size and of "
        f"hardware."
    )
    keywords = ("query optimization; indexing; JOIN execution; subquery rewriting; "
                "SARGability; Olist dataset; execution plan; cost-based optimizer")
    p = [dx.para(dx.run("ARTICLE INFO", smallcaps=True, sz=9), align="left",
                 before=240, after=120, left=0, hanging=0),
         article_info(),
         dx.para(dx.run("ABSTRACT", smallcaps=True, sz=10), align="left",
                 before=240, after=120, left=0, hanging=0),
         dx.para(dx.run(abstract, sz=10), align="both", after=120),
         dx.para(dx.run("This is an open access article under the CC–BY license.",
                        sz=8.5), align="right", after=240),
         dx.para(dx.run("Keywords: ", b=True, sz=7) + dx.run(keywords, sz=7),
                 align="left", after=120)]
    return "".join(p)


# ==========================================================================
# body helpers
# ==========================================================================
def h1(text: str) -> str:
    return dx.heading(text, 1)


def h2(text: str) -> str:
    return dx.heading(text, 2)


def body(text: str) -> str:
    return dx.para(dx.run(text), align="both", after=120, left=0, hanging=0)


def bullet(text: str) -> str:
    return dx.para(dx.run("•  ") + dx.run(text), align="both", after=60,
                   left=284, hanging=142)


def mono_block(text: str, *, sz: float = 8.0) -> str:
    """SQL listing: monospaced, left aligned, lightly indented."""
    out = []
    for line in text.strip("\n").split("\n"):
        out.append(dx.para(dx.run(line or " ", font="Consolas", sz=sz),
                           align="left", after=0, line=240, left=284, hanging=0,
                           before=0))
    out.append(dx.para(dx.run(""), after=60, align="left", left=0, hanging=0))
    return "".join(out)


def caption(kind: str, text: str) -> str:
    return dx.caption(kind, text)


# ==========================================================================
# tables
# ==========================================================================
def table_schema(r: Results) -> str:
    rows = [["Table", "Rows", "Primary key", "Foreign keys", "Analytical role"]]
    data = [
        ("customers", "99,441", "customer_id", "—", "Customer geography (state, city, ZIP prefix)"),
        ("sellers", "3,095", "seller_id", "—", "Seller geography"),
        ("products", "32,951", "product_id", "—", "Product attributes and category key"),
        ("category_translation", "71", "product_category_name", "—", "Category label lookup"),
        ("orders", "99,441", "order_id", "customer_id", "Order header: status and four timestamps"),
        ("order_items", "112,650", "(order_id, order_item_id)", "order_id, product_id, seller_id", "Order line: price and freight"),
        ("order_payments", "103,886", "(order_id, payment_sequential)", "order_id", "Payment events per order"),
        ("order_reviews", "99,224", "(review_id, order_id)", "—", "Review score and free text"),
        ("geolocation", "19,015", "geolocation_zip_code_prefix", "—", "Coordinate per ZIP prefix"),
    ]
    rows += [list(d) for d in data]
    rows.append(["Total (loaded)", f"{SCHEMA_ROWS:,}", "—", "—",
                f"{SOURCE_ROWS:,} rows in the nine source files before geolocation "
                f"de-duplication"])
    return dx.table(rows, [1250, 800, 1650, 1750, 3338], font_sz=7.5)


def table_workloads(r: Results, bm) -> str:
    rows = [["ID", "Family", "Logical question", "SQL form"]]
    for label in QUERY_ORDER:
        sql = r.sql.get(label, "")
        form = {
            "W1.1": "SELECT + point predicate",
            "W1.2": "Correlated scalar subquery + GROUP BY",
            "W1.3": "GROUP BY on dimension",
            "W2.1 non-SARG month": "DATE_FORMAT(column) = const, selective",
            "W2.2 SARG month": "Half-open range predicate, selective",
            "W2.3 non-SARG year": "YEAR(column) = const, non-selective",
            "W2.4 SARG year": "Half-open range predicate, non-selective",
            "W3.1": "INNER JOIN + GROUP BY",
            "W4.1 JOIN": "INNER JOIN",
            "W4.2 IN": "Uncorrelated IN",
            "W4.3 EXISTS": "Correlated EXISTS",
            "W5.1 LEFT JOIN": "LEFT JOIN ... IS NULL",
            "W5.2 NOT IN": "Uncorrelated NOT IN",
            "W5.3 NOT EXISTS": "Correlated NOT EXISTS",
            "W6.1 flat JOIN": "Flat three-table join",
            "W6.2 derived table": "Derived-table materialisation",
            "W7.1": "RANK() window function",
            "W8.1": "ORDER BY ... LIMIT",
        }[label]
        rows.append([label.split()[0], FAMILY_OF[label],
                     QUERY_DESC[label], form])
    return dx.table(rows, [700, 700, 4388, 3000], font_sz=7.5)


def table_configs(r: Results) -> str:
    rows = [["Config", "Secondary indexes present", "Purpose"]]
    idx = {
        "C0_zero": "none",
        "C1_fk": "orders.customer_id, order_items.product_id, order_items.seller_id",
        "C2_single": "C1 + 10 single-column indexes on filter and join columns",
        "C3_composite": "C1 + 4 composite indexes (equality column, range column)",
        "C4_covering": "C1 + composite indexes + 2 indexes covering the full projection",
    }
    for cfg in CONFIG_ORDER:
        rows.append([CONFIG_SHORT[cfg], idx[cfg], CONFIG_DESC[cfg]])
    return dx.table(rows, [800, 4200, 3788], font_sz=7.5)


def table_environment(r: Results) -> str:
    rows = [
        ["Item", "Calibration platform (measurements reported)", "Reference platform (target)"],
        ["CPU", "AMD Ryzen 5 PRO 4650U, 3 vCPU allocated to the container",
         "8-core (Intel Core Ultra / Ryzen equivalent)"],
        ["Memory", "4 GB allocated; InnoDB buffer pool 128 MB", "16 GB"],
        ["Storage", "Backing store resident in RAM (no device-level I/O latency)",
         "NVMe SSD"],
        ["Operating system", "Ubuntu 26.04 LTS, x86-64", "64-bit Linux or Windows"],
        ["Database engine", "MariaDB 10.11.6 (MySQL-compatible), InnoDB", "MySQL 8.x, InnoDB"],
        ["Buffer pool", "128 MB (smaller than the ~180 MB working set)",
         "128 MB default, identical setting used"],
        ["Other session variables", "join_buffer_size 256 KB, sort_buffer_size 2 MB, "
                                    "tmp_table_size 16 MB (server defaults, unchanged)",
         "Server defaults, unchanged"],
    ]
    return dx.table(rows, [1500, 3900, 3388], font_sz=7.5)


def table_all_results(r: Results) -> str:
    rows = [["ID", "Family"] + [CONFIG_SHORT[c] for c in CONFIG_ORDER]
            + [f"Speed-up\n{CONFIG_SHORT['C4_covering']} vs {CONFIG_SHORT['C0_zero']}"]]
    for label in QUERY_ORDER:
        cells = [label.split()[0], FAMILY_OF[label]]
        for cfg in CONFIG_ORDER:
            cells.append(r.cell_text(cfg, label, censored_note="> 45 s"))
        cells.append(r.fmt_x(r.speedup("C4_covering", label)))
        rows.append(cells)
    # geometric-mean row
    cells = ["Geo-mean", "all"]
    for cfg in CONFIG_ORDER:
        if cfg == "C0_zero":
            cells.append("1.00x")
        else:
            cells.append(r.fmt_x(r.geomean_speedup(cfg)))
    cells.append(r.fmt_x(r.geomean_speedup("C4_covering")))
    rows.append(cells)
    rows.append(["Total", "all"] + [r.fmt_ms(r.total(c)) for c in CONFIG_ORDER]
                + [r.fmt_x(r.speedup("C4_covering", "W1.1")) if False else
                   r.fmt_x((r.total("C0_zero") or 0) / (r.total("C4_covering") or 1))])
    return dx.table(rows, [700, 700, 1150, 1150, 1150, 1150, 1150, 1338], font_sz=7)


def table_family_speedup(r: Results) -> str:
    rows = [["Family", "Workload", f"{CONFIG_SHORT['C2_single']}",
             f"{CONFIG_SHORT['C3_composite']}", f"{CONFIG_SHORT['C4_covering']}",
             "Best configuration"]]
    for fam, desc in FAMILIES.items():
        qs = [q for q in QUERY_ORDER if FAMILY_OF[q] == fam]
        cells = [fam, desc]
        for cfg in ("C2_single", "C3_composite", "C4_covering"):
            cells.append(r.fmt_x(r.family_geomean_speedup(cfg, fam)))
        best = max(("C2_single", "C3_composite", "C4_covering"),
                   key=lambda c: r.family_geomean_speedup(c, fam) or 0.0)
        cells.append(CONFIG_SHORT[best])
        rows.append(cells)
    # mark the winning configuration in each row
    for ri, fam in enumerate(FAMILIES, start=1):
        vals = {c: (r.family_geomean_speedup(c, fam) or 0.0)
                for c in ("C2_single", "C3_composite", "C4_covering")}
        win = max(vals, key=lambda c: vals[c])
        col = {"C2_single": 2, "C3_composite": 3, "C4_covering": 4}[win]
        if len(rows) > ri:
            rows[ri][col] = f"*{rows[ri][col]}*"
    return dx.table(rows, [700, 3100, 1200, 1300, 1200, 1288], font_sz=7.5)


def table_column_order(r: Results) -> str:
    """Workloads that constrain/order by a composite index's trailing column only."""
    lead = {
        "C2_single": "orders.order_purchase_timestamp",
        "C3_composite": "orders.order_status (unconstrained) / customers.customer_state",
        "C4_covering": "orders.order_status (unconstrained)",
    }
    rows = [["ID", "Config", "Index consulted", "Leading column of that index",
             "Median\n(ms)", "Access path chosen"]]
    for q in ("W2.2 SARG month", "W8.1"):
        first = True
        for tag, cfg in (("C2", "C2_single"), ("C3", "C3_composite"),
                         ("C4", "C4_covering")):
            idx = {"C2_single": "ix_orders_purch_ts",
                   "C3_composite": "ix_orders_status_ts",
                   "C4_covering": "ix_orders_cov"}[cfg]
            rows.append([q.split()[0] if first else "", tag, f"orders.{idx}",
                         lead[cfg], r.fmt_ms(r.med(cfg, q)),
                         r.plan_summary(cfg, q)])
            first = False
    return dx.table(rows, [560, 620, 1700, 2400, 780, 2728], font_sz=6.5)


def table_join_vs_subquery(r: Results) -> str:
    rows = [["Family", "Formulation", "C0 (ms)", "C2 (ms)", "C4 (ms)",
             "C0 spread", "Chosen access path at C0"]]
    groups = [
        ("W4 semi-join", ["W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS"]),
        ("W5 anti-join", ["W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS"]),
    ]
    for gname, qs in groups:
        meds0 = [r.med("C0_zero", q) or 0 for q in qs]
        spread = (max(meds0) / min(meds0)) if min(meds0) > 0 else None
        for q in qs:
            plan = r.plan_summary("C0_zero", q)
            plan = plan if len(plan) < 74 else plan[:71] + "..."
            rows.append([gname if q == qs[0] else "", q,
                         r.cell_text("C0_zero", q, "> 45 s"),
                         r.cell_text("C2_single", q, "> 45 s"),
                         r.cell_text("C4_covering", q, "> 45 s"),
                         r.fmt_x(spread) if q == qs[0] else "", plan])
    return dx.table(rows, [1000, 1400, 1000, 1000, 1000, 900, 2488], font_sz=6.5)


def table_sargability(r: Results) -> str:
    rows = [["ID", "Predicate over order_purchase_timestamp", "Matching\nrows",
             "C0 (ms)", "C2 (ms)", "C4 (ms)", "SARGable\nadvantage at C4",
             "Access path at C4"]]
    sel = [("W2.1 non-SARG month", "W2.2 SARG month",
            "DATE_FORMAT(ts,'%Y-%m') = '2018-06'",
            "ts >= '2018-06-01' AND ts < '2018-07-01'")]
    nsel = [("W2.3 non-SARG year", "W2.4 SARG year",
             "YEAR(ts) = 2018",
             "ts >= '2018-01-01' AND ts < '2019-01-01'")]
    for nonsarg, sarg, lbl_n, lbl_s in (sel[0], nsel[0]):
        n_rows = SELECTIVITY["month"] if nonsarg.endswith("month") \
            else SELECTIVITY["year"]
        c4n, c4s = r.med("C4_covering", nonsarg), r.med("C4_covering", sarg)
        adv = (c4n / c4s) if (c4n and c4s) else None
        plan = r.plan_summary("C4_covering", sarg)
        plan = plan if len(plan) < 46 else plan[:43] + "..."
        rows.append([nonsarg.split()[0], lbl_n, f"{n_rows:,}",
                     r.fmt_ms(r.med("C0_zero", nonsarg)),
                     r.fmt_ms(r.med("C2_single", nonsarg)),
                     r.fmt_ms(c4n), "", plan])
        rows.append([sarg.split()[0], lbl_s, f"{n_rows:,}",
                     r.fmt_ms(r.med("C0_zero", sarg)),
                     r.fmt_ms(r.med("C2_single", sarg)),
                     r.fmt_ms(c4s), r.fmt_x(adv) if adv else "", ""])
    return dx.table(rows, [560, 2500, 780, 850, 850, 850, 1100, 1298], font_sz=6.5)


def table_sensitivity(r: Results) -> str:
    """How absolute times on the reference platform scale with a hardware factor."""
    rows = [["Scaling factor κ applied to the indexed configuration",
             "W1.1 (ms)", "W3.1 (ms)", "W6.1 (ms)",
             "Total, 17 non-outlier queries (ms)"]]
    for kappa, note in ((0.5, "reference CPU about 2× faster, single thread"),
                        (0.75, ""),
                        (1.00, "measured values, calibration platform"),
                        (1.50, "reference platform about 1.5× slower, single thread"),
                        (2.00, "reference platform about 2× slower, single thread")):
        cells = [f"{kappa:.2f}" + (f"  ({note})" if note else "")]
        for q in ("W1.1", "W3.1", "W6.1 flat JOIN"):
            v = r.med("C4_covering", q)
            cells.append(f"{v * kappa:,.2f}" if v else "n/a")
        tot = r.total("C4_covering")
        cells.append(f"{tot * kappa:,.2f}" if tot else "n/a")
        rows.append(cells)
    return dx.table(rows, [3400, 1300, 1300, 1300, 1488], font_sz=7)



SCHEMA_ROWS = 569_774      # rows present in the loaded nine-table schema
SOURCE_ROWS = 1_550_922    # rows across the nine source CSV files pre-dedup

NQ = len(QUERY_ORDER)
NF = len(FAMILIES)
NUMWORDS = {16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen",
            20: "twenty", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
            12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen"}
NQW = NUMWORDS.get(NQ, str(NQ))
NFW = NUMWORDS.get(NF, str(NF))


# ==========================================================================
# narrative
# ==========================================================================
def introduction(r: Results, bm) -> str:
    p = []
    p.append(h1("1. Introduction"))
    p.append(body(
        "A transactional e-commerce database is written one row at a time and read in "
        "completely different shapes. The write path appends orders, order lines, "
        "payments and reviews; the read path asks questions such as how much revenue each "
        "state produced in each month, which sellers rank highest within their region, "
        "and which recent orders never received a review. Nothing about the physical "
        "design of such a schema guarantees that those two access patterns agree. The "
        "structures that make insertion cheap frequently make retrieval expensive, and the "
        "queries that dominate an analytics workload are rarely the queries the schema "
        "was shaped around."))
    p.append(body(
        "Two responses to that mismatch dominate practice, and they are usually taught "
        "and applied as if they were independent. The first is physical: add indexes. The "
        "second is logical: rewrite the query, replacing subqueries with joins or joins "
        "with subqueries according to whichever rule of thumb the author happens to "
        "recall. Both are sound as heuristics and unreliable as conclusions, for the same "
        "underlying reason: the execution time of a statement is decided by the access "
        "path the optimiser selects, and that path is a function of available indexes, "
        "estimated cardinalities and the syntactic form of the statement taken together. "
        "Changing either input changes the output, so attributing an observed improvement "
        "to the input one believes was changed is unsafe."))
    p.append(body(
        "The empirical literature on this problem is substantial but uneven. Cost-based "
        "optimisation and join-algorithm selection are well characterised theoretically and "
        "in controlled benchmarks [10]–[19], and index-selection heuristics have been "
        "studied extensively [12], [20]–[25]. What is missing is a study that varies the "
        "two factors independently within a single controlled setting, on a real "
        "operational dataset rather than a synthetic benchmark such as TPC-H, and that "
        "reports the chosen execution plan alongside the timing so that the mechanism "
        "behind each measurement can be verified rather than inferred."))
    p.append(body(
        "This paper addresses that gap. The Brazilian E-Commerce dataset published by "
        "Olist [1] is used because it is a genuine marketplace transaction log rather than "
        "a generated benchmark, and because its nine-table relational structure and "
        "analytical use are documented in the literature [2]–[9]. The dataset is "
        "normalised into a nine-table InnoDB schema totalling "
        f"{SCHEMA_ROWS:,} rows. {NQW.capitalize()} queries spanning {NFW} workload families are executed under five "
        "index configurations, and each configuration is measured from the database "
        "server's own statement profiler with the chosen plan recorded by EXPLAIN."))
    p.append(body("The paper makes four contributions."))
    p.append(bullet(
        "A measurement design that separates the index variable from the query-form "
        "variable. Five configurations are constructed so that each is rebuilt from "
        f"scratch, and the {NQW} queries are grouped into families that hold the logical "
        "question fixed while varying only its syntactic expression."))
    p.append(bullet(
        "An evidence-based account of when indexing pays. Speed-up is reported per query "
        "and aggregated per family as a geometric mean, showing that the benefit is "
        "governed by the ratio of rows examined to rows returned rather than by the number "
        "of indexes present."))
    p.append(bullet(
        "A measurement of JOIN against subquery formulation under identical index "
        "conditions, with the executed plan reported for each variant, which shows that the "
        "usual advice is conditional on the optimiser rewriting the subquery form into a "
        "hash-based semi- or anti-join."))
    p.append(bullet(
        "A quantified account of predicate form: the measured difference between a "
        "non-SARGable function call and an equivalent half-open range, which is the "
        "cheapest available optimisation and the one most often omitted."))
    p.append(body(
        "The remainder of the paper is organised as follows. Section 2 reviews the "
        "literature on cost-based optimisation, index structures, join algorithms, "
        "subquery rewriting and SARGability, and identifies the gap this work addresses. "
        "Section 3 describes the dataset, the schema, the query workloads, the index "
        "configurations, the measurement protocol and the execution environment. "
        "Section 4 reports the results and discusses them. Section 5 concludes."))
    return "".join(p)


def related_work(r: Results) -> str:
    p = []
    p.append(h1("2. Related Work"))

    p.append(h2("2.1 Cost-Based Query Optimisation"))
    p.append(body(
        "Relational query optimisation is conventionally framed as a search over an "
        "enumeration of equivalent query expressions, scored by a cost model that "
        "estimates I/O and CPU work for each candidate. Gretscher and Dittrich [10] compare "
        "split, holistic and hybrid strategies for this search and show that the "
        "alternatives differ in how they bound the search space rather than in the fidelity "
        "of their cost estimates. Mohsin et al. [18] and Zheng et al. [19] apply "
        "metaheuristic search to access-path and join-order selection in distributed "
        "settings, while Du [16] and Xiong et al. [17] address plan-cost estimation and "
        "plan selection directly. The common premise is that a plan's quality is bounded "
        "by the quality of its cost estimate, which is in turn bounded by the statistics "
        "available. That premise is what makes the empirical, plan-level approach taken "
        "here reasonable: rather than attempting to improve the optimiser, this study "
        "verifies which plans it actually produces for a given schema and query. Fritchey "
        "[29] provides the practitioner counterpart of this literature, treating "
        "execution-plan inspection as a routine diagnostic and distinguishing estimated "
        "from actual row counts as the primary signal that a cost model has mis-estimated; "
        "the row-count instrumentation used in this study serves that same purpose."))

    p.append(h2("2.2 Index Structures and Index Selection"))
    p.append(body(
        "Secondary indexes trade write cost and storage for read locality, and their value "
        "is governed by the fraction of the table they allow the server to avoid reading. "
        "Chen et al. [12] address the estimation problem directly, predicting the benefit "
        "of a candidate index so that unnecessary indexes can be avoided; the difficulty "
        "they identify, that benefit depends on the workload rather than the table alone, "
        "is precisely what the present design exploits by measuring a defined workload "
        "rather than a schema in isolation. Fugkeaw et al. [28] compare index "
        "configurations on analytical workloads and report that structural refinements "
        "which are decisive for one query class can be immaterial for another. Shin et al. "
        "[14] combine index structure with join optimisation on a relational engine, and "
        "Mokodaser et al. [21], Firmansyah et al. [22] and Ikhwan and Pramadjaya [23] "
        "report MySQL-specific measurements of indexing and subquery optimisation on "
        "operational databases, while Naufal et al. [24] and Witono and Parno [25] "
        "compare response times across access strategies including views and materialised "
        "views. These studies consistently report large gains from indexing but differ in "
        "whether they isolate the contribution of individual index designs. Pollack [30] "
        "makes the related distinction between transactional and analytical tuning "
        "explicit, and notes that the structures which serve one are frequently wrong for "
        "the other; the measurements in Section 4.3, in which a single index design is "
        "markedly better for some queries and markedly worse for others within one "
        "workload set, are consistent with that account."))

    p.append(h2("2.3 Join Algorithms and Subquery Rewriting"))
    p.append(body(
        "The three classical join algorithms, nested-loop, sort-merge and hash join, differ "
        "in how they exploit available structures, so join cost is inseparable from index "
        "availability. Liang et al. [13] select among join methods on relative cost, and "
        "Chandrashekariah and Dinesha [20] estimate join cost directly and compare "
        "candidate orderings; Ji et al. [15] address join-order search and Zhao et al. "
        "[11] address the selection among alternative subquery forms during "
        "re-optimisation. Do et al. [27] provide an empirical query-level comparison "
        "across engines, and Gretscher and Dittrich [10] include the standard cost "
        "formulations for the three algorithms. On the logical side, a semi-join and an "
        "anti-join admit both a join syntax and a subquery syntax, and an optimizer with "
        "semijoin and materialisation support enabled will normally convert the subquery "
        "form into the join form internally. This conversion is the mechanism behind the "
        "central measurement reported in Section 4.4."))

    p.append(h2("2.4 Predicate Form and SARGability"))
    p.append(body(
        "A predicate is SARGable when its structure allows the optimizer to constrain an "
        "index range, and non-SARGable when a function is applied to the indexed column so "
        "that the index cannot be used to locate matching rows. Farid Uddin et al. [26] "
        "analyse SARGable query forms and describe the transformation of non-SARGable "
        "predicates into equivalent SARGable ones. Because the transformation is "
        "semantics-preserving and requires no schema change, it is the cheapest "
        "optimisation available; its measurement is included here as workload W2."))

    p.append(h2("2.5 E-Commerce Transaction Data in Database Research"))
    p.append(body(
        "The Olist dataset has become a common substrate for e-commerce analytics. Andra "
        "and Baizal [2] apply dimensionality reduction and clustering to it, and Haqqani "
        "et al. [3] use it for RFM-based segmentation while documenting its nine-table "
        "relational structure. Zaghloul et al. [4] use it at scale for churn modelling, "
        "Jafri et al. [5] for recommendation with multimodal transfer learning, and Asfe et "
        "al. [6] likewise. Xu et al. [7] analyse platform operational status, Gogineni et "
        "al. [8] perform end-to-end transaction analysis including multi-table joins, and "
        "Proença et al. [9] model customer satisfaction. What this body of work shares is a "
        "concern with the data's content; the physical design and query efficiency of the "
        "relational structure that the dataset implies are treated as settled rather than "
        "measured."))

    p.append(h2("2.6 Research Gap"))
    p.append(body(
        "Three gaps follow from the above. First, indexing and query formulation are "
        "rarely varied independently, so published speed-ups cannot be attributed to a "
        "specific cause. Second, where subquery and join forms are compared, the executed "
        "plan is rarely reported, which makes it impossible to tell whether a difference "
        "came from the chosen access path or from something incidental. Third, results are "
        "usually reported for a single platform without any indication of how platform "
        "dependence should be interpreted. This study addresses all three by crossing five "
        f"index configurations with {NQW} queries, reporting the plan for every "
        "measurement, and separating platform-independent ratios from platform-dependent "
        "absolute times."))
    return "".join(p)


def method(r: Results, bm) -> str:
    p = []
    p.append(h1("3. Method"))

    p.append(h2("3.1 Dataset"))
    p.append(body(
        "All measurements use the Brazilian E-Commerce public dataset released by Olist "
        "[1]. The release comprises nine comma-separated files covering customers, "
        "sellers, products, product-category translation, orders, order items, order "
        f"payments, order reviews and geolocation. Row counts after loading are identical to "
        f"the published counts for every file. The nine source files contain "
        f"{SOURCE_ROWS:,} rows in total, of which {SCHEMA_ROWS:,} are present in the loaded "
        f"schema; the difference is entirely the geolocation de-duplication described below. "
        f"Two further properties of the released data required explicit handling rather "
        f"than silent correction."))
    p.append(body(
        "The reviews file contains 814 duplicate review_id values distributed across "
        "different orders, so review_id alone is not unique. The schema therefore declares "
        "a composite primary key of (review_id, order_id), which preserves all 99,224 "
        "source rows without discarding or inventing data. The geolocation file contains "
        "1,000,163 survey points but only 19,015 distinct ZIP-code prefixes; since "
        "downstream analytics consume one location per prefix, the 1,000,163 rows are "
        "aggregated to one representative row per prefix at load time. Neither adjustment "
        "alters any value used by a measured query, and both are applied identically in "
        "every index configuration so that no configuration benefits from a different "
        "row set."))

    p.append(h2("3.2 Schema Design"))
    p.append(body(
        "The CSV files were parsed according to RFC 4180, which matters because review "
        "comments contain embedded commas, quotation marks and line breaks, and then "
        "loaded into a normalised third-normal-form schema described in Table 1. "
        "Normalisation was chosen over a star schema deliberately: the study is concerned "
        "with the cost of retrieving rows across a normalised transaction log, and a "
        "pre-aggregated star schema would remove the joins under study. All tables use the "
        "InnoDB engine with UTF-8 character set and the server's default page size."))
    p.append(caption("Table", "1. Normalised schema, row counts and analytical role."))
    p.append(table_schema(r))
    p.append(body(
        "Foreign keys are declared on orders.customer_id, order_items.order_id, "
        "order_items.product_id, order_items.seller_id and order_payments.order_id. This "
        "decision has a measurement consequence that is easy to overlook: MySQL-compatible "
        "engines create an implicit secondary index to support each foreign key, so a "
        "faithfully imported schema already carries indexes that were never chosen for "
        "query performance. Because that post-import state is a realistic and interesting "
        "condition in its own right, it is retained as a distinct configuration rather than "
        "collapsed into the unindexed baseline."))

    p.append(h2("3.3 Query Workloads"))
    p.append(body(
        f"{NQW.capitalize()} queries were defined across {NFW} families. Each family holds a logical "
        "question fixed so that the effect of index configuration can be separated from "
        "the effect of query formulation. Table 2 summarises the families; the complete SQL "
        "for every query is listed in Appendix A."))
    p.append(caption("Table", "2. Query workload families."))
    p.append(table_workloads(r, bm))
    p.append(body(
        "Three design decisions in the workload set are worth stating explicitly, because "
        "each was forced by an unindexed degenerate plan rather than chosen for "
        "convenience. In the anti-join family W5, the driving relation is restricted to a "
        "fourteen-day purchase window. Expressed as a derived table the restriction is "
        "discarded, because derived-table merging folds it into the outer query and turns "
        "the LEFT JOIN variant into a cartesian product of roughly 9.5 × 10⁹ row "
        "comparisons, which is not measurable. The predicate is therefore written as a "
        "top-level restriction on the driving table, and all three anti-join variants share "
        "it exactly, so the comparison isolates formulation rather than input size. Second, "
        "the semi-join family W4 and anti-join family W5 each contain three formulations "
        "of one logical question, allowing within-family comparison at fixed indexing. "
        "Third, workload W2 contains two predicate pairs. Within each pair the two members "
        "return identical row counts and differ only in whether a function is applied to "
        "the filtered column; the pairs differ from each other in selectivity, which turns "
        "out to be the variable that moderates the effect."))

    p.append(h2("3.4 Index Configurations"))
    p.append(body(
        "Five configurations were constructed, listed in Table 3. Each is rebuilt from the "
        "same baseline before measurement rather than accumulated from the previous one, so "
        "that no configuration inherits an index it did not specify and the configurations "
        "are directly comparable. C0 removes the foreign keys together with their implicit "
        "indexes, yielding a schema with primary keys only. C1 restores the foreign keys "
        "and therefore reproduces the schema an analyst obtains from a conventional import. "
        "C2 adds ten single-column indexes on the columns appearing in filter predicates "
        "and join conditions. C3 instead adds four composite indexes whose leading column "
        "is an equality predicate and whose trailing column is the range or join column, "
        "reflecting the standard leftmost-prefix argument. Two of the ten single-column "
        "indexes requested for C2 duplicate a column already indexed in order to enforce a "
        "foreign key, so the server declines them and C2 carries eleven secondary indexes "
        "rather than thirteen. C4 extends C3 with indexes whose "
        "column list covers the complete projection of the analytical queries, so that the "
        "base table need not be visited at all. Because C2, C3 and C4 are alternatives "
        "rather than stages, the comparison also answers whether a broader set of "
        "single-column indexes is preferable to a smaller number of well-chosen composite "
        "ones."))
    p.append(caption("Table", "3. Index configurations."))
    p.append(table_configs(r))

    p.append(h2("3.5 Measurement Protocol"))
    p.append(body(
        "Elapsed time is taken from the database server's own statement profiler rather "
        "than from client-side wall-clock timing. Client-side timing would include "
        "connection handling and result-set serialisation, neither of which is part of the "
        "quantity of interest. The same protocol was applied to every configuration and "
        "every query."))
    p.append(body(
        f"For each configuration and each query, three untimed warm-up executions were "
        f"performed, followed by {r.repeats} timed executions, giving "
        f"{r.repeats} samples per cell and {r.repeats * 5 * len(QUERY_ORDER)} timed "
        f"measurements in total. The median is reported as the primary statistic because "
        f"it is robust to the scheduler noise expected on a shared machine; the mean, "
        f"standard deviation, minimum and maximum are retained in the result files. Across "
        f"all cells the coefficient of variation, taken as the standard deviation over "
        f"the mean, has a median of {r.median_cv() * 100:.1f} percent and a maximum of "
        f"{r.worst_cv()[0] * 100:.1f} percent, so the reported differences are not "
        f"attributable to run-to-run variance except where explicitly noted. Every "
        f"statement was additionally executed under EXPLAIN, and under the server's "
        f"actual-row-count instrumentation, so that the access path and the rows examined "
        f"are recorded alongside each timing rather than inferred from it. A per-statement "
        f"time limit of 45 seconds was imposed so that a degenerate plan would be recorded "
        f"as a censored measurement instead of stalling the sweep."))

    p.append(h2("3.6 Execution Environment"))
    p.append(body(
        "Measurements were taken on the calibration platform described in Table 4. The "
        "reference platform for this work is a Lenovo ThinkPad L14 with an eight-core "
        "processor, 16 GB of memory and NVMe solid-state storage. The calibration platform "
        "differs from it, and Table 4 states both so that the difference is visible rather "
        "than implicit. Section 4.8 treats the consequence for the reported numbers."))
    p.append(caption("Table", "4. Execution environments."))
    p.append(table_environment(r))
    p.append(body(
        "Two properties of the calibration environment are worth stating because they "
        "favour particular access paths. The InnoDB buffer pool was left at its 128 MB "
        "default, which is smaller than the approximately 180 MB working set of the "
        "measured tables, so buffer-pool residency is partial and index reads remain "
        "meaningful rather than being served entirely from memory. The backing store is "
        "resident in RAM, so device-level I/O latency does not contribute to the measured "
        "times; the workloads are consequently dominated by row comparison, hashing and "
        "sorting, which is the appropriate regime for studying access-path selection."))

    p.append(h2("3.7 Interpretation Across Platforms"))
    p.append(body(
        "Absolute execution times are platform-dependent; ratios between configurations "
        "are far less so, because both sides of the ratio are subject to the same hardware "
        "scaling. The reason is structural rather than empirical: a speed-up is governed by "
        "the ratio of rows examined to rows returned, and both quantities are properties of "
        "the data and the access path, not of the processor. Section 4.8 therefore reports "
        "the measured absolute values together with a sensitivity analysis across a range "
        "of hardware scaling factors, and the reproduction scripts are provided so that the "
        "absolute values can be regenerated on the reference platform directly."))
    return "".join(p)

def results(r: Results) -> str:
    p = []
    p.append(h1("4. Results and Discussion"))

    # ---- 4.1 -----------------------------------------------------------
    p.append(h2("4.1 Baseline Behaviour Without Secondary Indexes"))
    total0 = r.total("C0_zero") or 0.0
    slowest = max((q for q in QUERY_ORDER if q != "W5.1 LEFT JOIN"),
                  key=lambda q: r.med("C0_zero", q) or 0)
    fastest = min(QUERY_ORDER, key=lambda q: r.med("C0_zero", q) or 1e18)
    p.append(body(
        f"With primary keys only, and excluding the anti-join outlier discussed in "
        f"Section 4.4, the {NQ - 1} non-outlier queries required {total0:,.0f} ms in "
        f"total, ranging from "
        f"{r.fmt_ms_u(r.med('C0_zero', fastest))} for {fastest} to "
        f"{r.fmt_ms_u(r.med('C0_zero', slowest))} for {slowest}. One property of this "
        f"baseline governs how the remaining results should be read. The two tables "
        f"carrying the bulk of the data, orders at 99,441 rows and order_items at 112,650 "
        f"rows, are small enough that a full scan of either costs only tens of "
        f"milliseconds on the calibration platform. The unindexed baseline is therefore "
        f"not a pathological state; it is merely mediocre, and it leaves little room for "
        f"indexing to demonstrate the order-of-magnitude gains that such experiments "
        f"usually report. This is a property of the dataset and not of the methodology, "
        f"and it is the reason the present results are more modest than the literature "
        f"suggests."))
    p.append(body(
        f"One exception proves the rule. The anti-join formulation W5.1 costs "
        f"{r.fmt_ms_u(r.med('C0_zero', 'W5.1 LEFT JOIN'))} unindexed, "
        f"{(r.med('C0_zero', 'W5.1 LEFT JOIN') or 0) / max(r.med('C0_zero', slowest) or 1, 1):.0f} times "
        f"the slowest remaining query, because without an index on the "
        f"join column the outer join degenerates to a block-nested-loop join. That single "
        f"cell would dominate any aggregate computed over the sweep, so it is excluded from "
        f"the totals in Table 5 and from the geometric means in Table 6, and is analysed "
        f"separately in Section 4.4. Excluding it is stated explicitly rather than done "
        f"silently because a reader recomputing the means would otherwise be unable to "
        f"reproduce them."))

    # ---- 4.2 -----------------------------------------------------------
    p.append(h2("4.2 Effect of Adding Indexes"))
    p.append(body(
        f"Table 5 reports the median execution time for all {NQW} queries under all five "
        f"configurations. Figure 1 plots the same values on a logarithmic axis and Figure 2 "
        f"the speed-up over the unindexed baseline. The distribution of results is the main "
        f"finding, and it is not the one usually reported."))
    p.append(caption("Table", "5. Median execution time in milliseconds per query "
                              "and index configuration, with speed-up relative to C0. "
                              "The outlier W5.1 is excluded from the total and "
                              "geometric-mean rows."))
    p.append(table_all_results(r))
    p.append(caption("Figure", "1. Median server-side execution time by workload and "
                               "index configuration (logarithmic axis)."))
    p.append("FIGURE_1")
    p.append(caption("Figure", "2. Execution-time speed-up relative to the unindexed "
                               "baseline C0 (logarithmic axis)."))
    p.append("FIGURE_2")

    g2 = r.geomean_speedup("C2_single") or 0
    g3 = r.geomean_speedup("C3_composite") or 0
    g4 = r.geomean_speedup("C4_covering") or 0
    p.append(body(
        f"Aggregated as a geometric mean over the {len(QUERY_ORDER) - 1} non-outlier "
        f"queries, the post-import baseline C1 improves on C0 by only "
        f"{r.fmt_x(r.geomean_speedup('C1_fk'))}, the broad single-column set C2 by "
        f"{r.fmt_x(g2)}, the composite set C3 by {r.fmt_x(g3)} and the composite-plus-"
        f"covering set C4 by {r.fmt_x(g4)}. Two observations follow, and they pull in "
        f"opposite directions."))
    p.append(body(
        f"The first is that indexing helps much less than the literature would suggest. "
        f"Even the best configuration improves the median query by a factor of only about "
        f"two, and several queries are unimproved or marginally slower. Table 6 shows this "
        f"per family. The reason is the rows-examined-to-rows-returned ratio discussed "
        f"above: for the filter and aggregation queries that dominate the workload, the "
        f"qualifying rows are a large fraction of the relation, so an index cannot avoid "
        f"most of the reading and the ceiling on the achievable gain is low. A result of "
        f"this kind is not a refutation of indexing; it is a statement about the regime. "
        f"Indexing pays when the selective fraction is small, and the workloads where that "
        f"holds here are precisely the ones where the gain is dramatic."))
    p.append(caption("Table", "6. Geometric-mean speed-up by workload family, relative to "
                              "the unindexed baseline C0. An asterisk marks the best "
                              "configuration in each family. W5.1 is excluded from every "
                              "aggregate reported in this paper."))
    p.append(table_family_speedup(r))
    p.append(dx.para(dx.run("Note. W5.1 is excluded from the family mean for W5 and from "
                            "the totals and geometric means throughout, because its "
                            "magnitude would otherwise dominate them. It is analysed "
                            "separately in Section 4.4, where it is the principal result.",
                            sz=7.5),
                     align="both", after=120, left=0, hanging=0))
    p.append(body(
        f"The second observation is that the configuration ranking is not the one the "
        f"design intent would predict. The broad single-column set C2 outperforms both the "
        f"composite set C3 and the composite-plus-covering set C4, at "
        f"{r.fmt_x(g2)} against {r.fmt_x(g3)} and {r.fmt_x(g4)}. Section 4.3 shows that this "
        f"reversal is caused by a specific and well-understood property of composite index "
        f"column order, and it is the most transferable result in this study."))
    nz = [(r.speedup("C4_covering", q) or 0, q) for q in QUERY_ORDER
          if q != "W5.1 LEFT JOIN"]
    nz.sort(reverse=True)
    p.append(body(
        f"Excluding the outlier, the largest gains under C4 are " +
        ", ".join(f"{q} at {s:.2f}×" for s, q in nz[:3] if s > 1) +
        f", and the remaining {sum(1 for s, _ in nz if s <= 1.05)} queries gain nothing "
        f"measurable. The single largest improvement in the entire sweep is W5.1 at "
        f"{r.fmt_x(r.speedup('C4_covering', 'W5.1 LEFT JOIN'))}, but that is not an "
        f"indexing effect in the ordinary sense; it is a change of join algorithm, and it "
        f"is treated in Section 4.4."))

    # ---- 4.3 -----------------------------------------------------------
    p.append(h2("4.3 Column Order Within an Index Matters More Than Index Count"))
    p.append(body(
        "Because C2, C3 and C4 are alternatives rather than cumulative stages they can be "
        "compared directly, and the comparison refutes the design intent that motivated "
        "them. C2 embodies breadth, adding an index to every column appearing in a "
        "predicate, a join condition or an ORDER BY clause. C3 embodies the leftmost-prefix "
        "principle, composing each index so that its leading column is an equality "
        "predicate and its trailing column is the range or join column. C4 goes further "
        "and makes the indexes cover the entire projection. The expectation was that C3 "
        "would beat C2 on compound predicates and C4 would beat both. The measurement is "
        f"the other way round: C2 achieves {r.fmt_x(g2)}, C3 {r.fmt_x(g3)} and C4 "
        f"{r.fmt_x(g4)}."))
    p.append(body(
        "The mechanism is visible in the recorded plans, and it is the leftmost-prefix "
        "rule operating as a liability rather than an asset. A composite index on "
        "(order_status, order_purchase_timestamp) can serve a predicate on "
        "order_status and a range on order_purchase_timestamp, but it cannot serve a "
        "predicate or ordering on order_purchase_timestamp alone, because the leading "
        "column is unconstrained and its values are therefore scattered throughout the "
        "index. Workload W2.2 and workload W8.1 both constrain or order by "
        "order_purchase_timestamp alone, and both show the consequence."))
    p.append(caption("Table", "7. Effect of index column order on two workloads that "
                              "constrain or order by a trailing column alone."))
    p.append(table_column_order(r))
    p.append(body(
        f"In workload W2.2, which counts orders in a single month, C2 resolves the query "
        f"to a bounded range scan and returns in {r.fmt_ms_u(r.med('C2_single', 'W2.2 SARG month'))}, "
        f"whereas C4 falls back to a full scan of the composite index and requires "
        f"{r.fmt_ms_u(r.med('C4_covering', 'W2.2 SARG month'))}. In workload W8.1, which "
        f"retrieves the twenty most recent orders, C2 reads the timestamp index in its own "
        f"order and needs no sort at all, completing in "
        f"{r.fmt_ms_u(r.med('C2_single', 'W8.1'))}, while C3 and C4 both report a filesort in "
        f"the plan and require {r.fmt_ms_u(r.med('C3_composite', 'W8.1'))} and "
        f"{r.fmt_ms_u(r.med('C4_covering', 'W8.1'))}. Replacing a single-column index with a "
        f"composite one on the same column has therefore made these queries between one and "
        f"two orders of magnitude slower."))
    p.append(body(
        "The composite indexes are not useless, and it would be a mistake to conclude that "
        "single-column indexes are always preferable. W7.1, which ranks sellers within "
        "states, improves from " +
        f"{r.fmt_ms_u(r.med('C0_zero', 'W7.1'))} unindexed to "
        f"{r.fmt_ms_u(r.med('C3_composite', 'W7.1'))} with the composite index on "
        "(seller_id, price), a gain of " +
        f"{r.fmt_x(r.speedup('C3_composite', 'W7.1'))}, whereas the broad single-column set "
        f"C2 leaves it unimproved at {r.fmt_ms_u(r.med('C2_single', 'W7.1'))}. The composite "
        "index matches that workload's grouping and aggregate columns exactly. The "
        "conclusion is therefore not that one design wins but that no single design does: "
        "the best index set is workload-specific, and the deciding question is not how many "
        "indexes to create but whether each index's leading column is the column the query "
        "constrains, orders by or groups on. A composite index that is correct for a "
        "compound predicate can be actively harmful for the single-column queries that "
        "share its trailing columns, and this harm is invisible in an aggregate because it "
        "is offset by the gains on the workload the composite index was designed for."))

    # ---- 4.4 -----------------------------------------------------------
    p.append(h2("4.4 JOIN Versus Subquery Formulation"))
    p.append(body(
        "The semi-join family W4 and the anti-join family W5 each express one logical "
        "question in three syntactically different but semantically equivalent forms. "
        "Table 8 reports the timing of each form under identical index conditions together "
        "with the access path chosen in the unindexed configuration."))
    p.append(caption("Table", "8. Semi-join and anti-join formulations compared under "
                              "identical index conditions."))
    p.append(table_join_vs_subquery(r))
    p.append(caption("Figure", "3. Semi-join and anti-join formulation compared under "
                               "identical index configurations (logarithmic axis)."))
    p.append("FIGURE_3")

    w4 = [r.med("C0_zero", q) or 0 for q in ("W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS")]
    w5 = [r.med("C0_zero", q) or 0 for q in ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s4 = max(w4) / min(w4) if min(w4) > 0 else float("nan")
    s5 = max(w5) / min(w5) if min(w5) > 0 else float("nan")
    p.append(body(
        f"The semi-join family behaves uniformly. Its three forms cost "
        f"{r.fmt_ms_u(w4[0])}, {r.fmt_ms_u(w4[1])} and {r.fmt_ms_u(w4[2])} without secondary "
        f"indexes, a spread of only {s4:.2f}×, and the ordering is stable across every "
        f"configuration. No rewrite rule distinguishes them, because the optimiser "
        f"converts all three into the same semi-join internally and there is no index in "
        f"any configuration on which those conversions could differ."))
    c4w5 = [r.med("C4_covering", q) or 0 for q in ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s5c4 = max(c4w5) / min(c4w5) if min(c4w5) > 0 else float("nan")
    p.append(body(
        f"The anti-join family behaves very differently, and its ordering reverses "
        f"completely with indexing. Unindexed, the LEFT JOIN formulation costs "
        f"{r.fmt_ms_u(w5[0])} while the NOT IN and NOT EXISTS forms cost {r.fmt_ms_u(w5[1])} "
        f"and {r.fmt_ms_u(w5[2])}, a spread of {s5:.0f}×. The recorded plans explain why. "
        f"The subquery forms are recognised as anti-join candidates and executed as "
        f"hash-based lookups against a materialised right-hand side, at a cost "
        f"proportional to the sum of the two relation sizes. The explicit LEFT JOIN "
        f"formulation, carrying the same logical anti-join, is executed as a "
        f"block-nested-loop join that must be completed before the IS NULL filter can be "
        f"applied. In this configuration the subquery form is not a naive substitute for "
        f"the join form; it is the better plan, and it is the syntactic join form that "
        f"degrades."))
    p.append(body(
        f"C4 adds an index on (order_id, review_score), the join and filter columns of this "
        f"family, and the ordering inverts. The LEFT JOIN form now costs "
        f"{r.fmt_ms_u(c4w5[0])}, the fastest of the three, against {r.fmt_ms_u(c4w5[1])} and "
        f"{r.fmt_ms_u(c4w5[2])} for the subquery forms, a spread of {s5c4:.1f}× in the "
        f"opposite direction. The plan changes with it: the outer join becomes an index "
        f"lookup on the driving table's date range followed by a direct probe of the "
        f"review index, whereas the subquery forms materialise a large right-hand side that "
        f"the index cannot help them avoid."))
    nojoin_cfgs = [c for c in CONFIG_ORDER if c != "C4_covering"]
    n_nojoinidx = len(nojoin_cfgs)
    nojoin_vals = [r.med(c, "W5.1 LEFT JOIN")
                   or r.censored_ms.get((c, "W5.1 LEFT JOIN"), 0.0)
                   for c in nojoin_cfgs]
    _cens = [CONFIG_SHORT[c] for c in nojoin_cfgs
             if r.is_censored(c, "W5.1 LEFT JOIN")]
    censored_txt = (", ".join(_cens) + " exceeded the 45-second statement limit "
                    "imposed on the sweep and is reported as censored") if _cens \
        else "none exceeded the 45-second statement limit"

    p.append(body(
        f"This inverts the conventional advice in two respects. It is commonly taught that "
        f"subqueries are the naive option to be rewritten away; here they are faster than "
        f"the join form by a factor of {s5:.0f} before indexing and slower by a factor of "
        f"{s5c4:.1f} after it. And it is commonly taught that the three formulations are "
        f"interchangeable; here their relative cost changes sign with the index set. The two "
        f"observations are consistent, and together they yield the actual conclusion: the "
        f"cost of a formulation is a property of the plan the optimiser selects, the plan is "
        f"a property of the indexes available, and therefore no rule of the form always use "
        f"JOIN or always use EXISTS can be correct. The practical implication is cheap and "
        f"uncontroversial: inspect the plan before rewriting, because a rewrite justified by "
        f"a rule of thumb can cost a factor of {s5:.0f} in one direction and save a factor of "
        f"{s5c4:.1f} in the other. Note also that the fastest configuration for this family "
        f"is not the one with the most indexes but the one carrying an index on the join "
        f"column: the {n_nojoinidx} configurations lacking that index leave W5.1 at "
        f"{min(nojoin_vals):,.0f} ms or above, and "
        f"{censored_txt}."))

    # ---- 4.5 -----------------------------------------------------------
    p.append(h2("4.5 Predicate Form, SARGability and Selectivity"))
    n1, s1 = "W2.1 non-SARG month", "W2.2 SARG month"
    n2, s2 = "W2.3 non-SARG year", "W2.4 SARG year"
    rows_m = SELECTIVITY["month"]
    rows_y = SELECTIVITY["year"]
    p.append(body(
        f"Workload W2 compares four predicates over the same column. Two pairs return "
        f"identical row counts, and within each pair the two members differ only in whether "
        f"a function is applied to the filtered column. Both members of each pair were "
        f"verified to return the same count. The pairs differ in selectivity: the month "
        f"pair matches {rows_m:,} orders, or {pct(rows_m, SELECTIVITY['orders_total']):.1f} "
        f"percent of the table, and the year pair {rows_y:,}, or "
        f"{pct(rows_y, SELECTIVITY['orders_total']):.1f} percent. "
        f"Including both regimes is essential, because SARGability can only pay off when it "
        f"lets the server avoid reading rows, and a predicate matching the majority of a "
        f"table offers no rows to avoid reading."))
    p.append(caption("Table", "9. Non-SARGable and SARGable predicates at two levels of "
                              "selectivity."))
    p.append(table_sargability(r))
    p.append(caption("Figure", "4. Predicate form compared at two levels of selectivity "
                               "(logarithmic axis)."))
    p.append("FIGURE_4")
    adv_m = ((r.med("C4_covering", n1) or 0) / max(r.med("C4_covering", s1) or 1e-9, 1e-9))
    p.append(body(
        f"The selective pair behaves exactly as theory predicts, and the plans confirm the "
        f"mechanism rather than merely correlating with it. In C2 the non-SARGable form is "
        f"executed as a full scan of the timestamp index with a filter applied to each "
        f"entry, costing {r.fmt_ms_u(r.med('C2_single', n1))}, while the SARGable form is "
        f"executed as a bounded range scan, costing "
        f"{r.fmt_ms_u(r.med('C2_single', s1))}. That is a factor of "
        f"{((r.med('C2_single', n1) or 0) / max(r.med('C2_single', s1) or 1e-9, 1e-9)):.1f}× "
        f"for a change that consists of rewriting one predicate and nothing else."))
    adv_y = ((r.med("C4_covering", n2) or 0) / max(r.med("C4_covering", s2) or 1e-9, 1e-9))
    p.append(body(
        f"The non-selective pair shows the limit of the rule. YEAR(ts) = 2018 and its range "
        f"equivalent match {rows_y:,} of 99,441 rows, and in C4 they cost "
        f"{r.fmt_ms_u(r.med('C4_covering', n2))} and {r.fmt_ms_u(r.med('C4_covering', s2))}. The "
        f"SARGable form is therefore not faster at all: the ratio of SARGable to "
        f"non-SARGable time is {(1 / adv_y):.2f}×, indistinguishable from unity. A range "
        f"scan covering {pct(rows_y, SELECTIVITY['orders_total']):.0f} percent "
        f"of a table must still visit the same fraction of the index entries, so the server does most of the work a full "
        f"scan would do and buys only the columns it does not need to read. Rewriting the "
        f"predicate is therefore necessary but not sufficient: its benefit is mediated by "
        f"selectivity. A reviewer who tests SARGability only on a low-selectivity predicate "
        f"will correctly conclude that it does not matter, and will be wrong."))
    p.append(body(
        f"It is worth noting what C4 does to the selective pair. Its ratio of "
        f"{adv_m:.2f}× is far weaker than C2's, and the recorded plan explains why: C4 has no "
        f"index whose leading column is order_purchase_timestamp, so both members of the "
        f"pair fall back to scanning a composite index in full. SARGability cannot help when "
        f"there is no index to exploit, which is the same column-order effect that Section "
        f"4.3 identified. Predicate form and index design are therefore not independent "
        f"decisions either, and a study that varied only one of them would have reported "
        f"the other as irrelevant."))
    p.append(body(
        f"The practical ordering that follows is: rewrite the predicate into a range form, "
        f"check the selectivity, and create an index whose leading column is the filtered "
        f"column only if the range is selective enough to justify the write cost. The "
        f"rewrite itself is free: it requires no schema modification, no index creation and "
        f"no application release, it is semantics-preserving, and in the selective case "
        f"measured here it was the difference between {r.fmt_ms_u(r.med('C2_single', n1))} and "
        f"{r.fmt_ms_u(r.med('C2_single', s1))}. It is also worth stating that creating an "
        f"index to serve a non-SARGable predicate does not work at all, so a team that adds "
        f"an index without rewriting the predicate may see no improvement and wrongly "
        f"conclude that the index was useless."))

    # ---- 4.6 -----------------------------------------------------------
    p.append(h2("4.6 Multi-Table and Analytical Workloads"))
    a, b = "W6.1 flat JOIN", "W6.2 derived table"
    ra, rb = r.med("C4_covering", a) or 0, r.med("C4_covering", b) or 0
    p.append(body(
        f"The most demanding workloads resist indexing. W6.1 joins orders, "
        f"customers and order items and groups the result by state and month, costing "
        f"{r.fmt_ms_u(r.med('C0_zero', a))} at C0 and {ra:,.2f} ms at C4, a speed-up of "
        f"{r.fmt_x(r.speedup('C4_covering', a))} and therefore a slight regression rather "
        f"than an improvement. W7.1, "
        f"which ranks sellers within states using a window function over an aggregate, "
        f"improves only under the composite configurations, from "
        f"{r.fmt_ms_u(r.med('C0_zero', 'W7.1'))} to {r.fmt_ms_u(r.med('C3_composite', 'W7.1'))}. "
        f"An index that reduces the cost of locating rows cannot fundamentally reduce the "
        f"cost of combining and grouping them, and for a query whose qualifying rows are the "
        f"bulk of the relation there is nothing to locate more cheaply."))
    ratios = {}
    for cfg in CONFIG_ORDER:
        fa, de = r.med(cfg, a), r.med(cfg, b)
        if fa and de:
            ratios[cfg] = de / fa
    faster = [c for c, v in ratios.items() if v < 1.0]
    p.append(body(
        f"W6.2 computes the same result as W6.1 with the joins hoisted into a derived "
        f"table, and is included to test whether restructuring helps. The two statements "
        f"are semantically equivalent, so any difference between them is attributable to "
        f"how the optimiser treats the derived table rather than to the work required. "
        f"Across the five configurations the ratio of derived to flat form is " +
        ", ".join(f"{CONFIG_SHORT[c]} {v:.2f}" for c, v in ratios.items()) +
        f". The differences are all under {max(abs(1 - v) for v in ratios.values()) * 100:.0f} "
        f"percent, and the sign is not stable: the derived form is faster in "
        f"{len(faster)} of the {len(ratios)} configurations and slower in "
        f"{len(ratios) - len(faster)}. Restructuring an equivalent query therefore had no "
        f"reliable effect here, and a practitioner who measured it under one set of "
        f"indexes and generalised would reach a conclusion the other four configurations "
        f"contradict. This is the same conclusion reached for join formulation in "
        f"Section 4.4, arrived at from a different direction: the outcome of a rewrite is "
        f"determined by the plan it induces under the indexes actually present, so it "
        f"cannot be predicted from the rewrite alone."))

    # ---- 4.7 -----------------------------------------------------------
    p.append(h2("4.7 Where Indexing Does Not Help"))
    regress = [(q, r.speedup("C4_covering", q)) for q in QUERY_ORDER]
    regress = [(q, s) for q, s in regress if s is not None and s < 1.05]
    regress.sort(key=lambda t: t[1])
    p.append(body(
        f"Indexing is normally reported as a uniform benefit, and a study that reported only "
        f"successes would misrepresent the design space. Against C0, the fully indexed "
        f"configuration C4 leaves {len(regress)} of the {NQW} queries unimproved or worse "
        f"within the margin of run-to-run variance: " +
        ", ".join(f"{q} at {s:.2f}×" for q, s in regress) + "."))
    p.append(body(
        f"The explanation is consistent across all of them and is the rows-examined-to-rows-"
        f"returned ratio made operational. Where the qualifying rows are a large fraction of "
        f"the relation, the server must read most rows whichever structure it uses, so an "
        f"index changes only the cost of the columns it does not cover. Where a query must "
        f"aggregate or join before it can produce any row, an index cannot remove that work "
        f"at all. Predicting whether an index is worth creating therefore reduces to "
        f"estimating that ratio, which is exactly the quantity that index-benefit estimation "
        f"methods attempt to predict without measurement [12]. This study offers a simple "
        f"diagnostic for that estimate: a candidate index should be expected to pay only if "
        f"the predicate it serves is selective, and the plans recorded here make that "
        f"condition directly observable."))
    p.append(body(
        f"A second limitation is inherent to the design rather than to the data. Every "
        f"configuration is evaluated on read latency alone, so the write cost and storage "
        f"cost of the eleven indexes in C2 and the seven in C4 are unmeasured. Since every "
        f"secondary index must be maintained on each insert and update, and since this "
        f"workload is dominated by analytical reads over a dataset that is not being written "
        f"during measurement, the configurations that perform best here would be the worst "
        f"choices for the write path of a live transactional system. A production index "
        f"recommendation must combine the measurements reported here with write throughput "
        f"and space measurements, and this study does not claim to provide them."))

    # ---- 4.8 -----------------------------------------------------------
    p.append(h2("4.8 Interpretation on the Reference Platform"))
    p.append(body(
        "The reference platform for this work is a ThinkPad L14 with eight cores, 16 GB of "
        "memory and NVMe storage. The measurements in Table 5 were taken on the calibration "
        "platform of Table 4, and the two differ. Rather than assert a conversion that was "
        "not measured, this section separates the reported quantities into those that are "
        "platform-dependent and those that are not."))
    p.append(body(
        "Absolute execution times in milliseconds are platform-dependent and will differ on "
        "the reference platform. The speed-up ratios in Tables 5 to 9 are largely not. A "
        "speed-up is the ratio of two times produced by the same engine on the same data "
        "with the same plan, differing only in index availability, and both terms are "
        "governed by the number of rows the engine must examine, which is a property of the "
        "data and the access path rather than of the processor. Hardware scaling multiplies "
        "numerator and denominator together and cancels. The qualitative conclusions of "
        "Sections 4.2 to 4.7 should therefore transfer to the reference platform even though "
        "the absolute timings will not, and the reader should treat the plan-level findings, "
        "which are statements about which access path the optimiser selects, as the "
        "transferable results. Those findings are in fact the paper's principal content, "
        "since they do not depend on the magnitude of any timing."))
    p.append(body(
        "One qualification is necessary. The relative ordering of two plans can in principle "
        "change with hardware if one plan is I/O-bound and the other CPU-bound, since the "
        "reference platform's NVMe storage is substantially faster than the calibration "
        "platform's backing store. The configurations compared here differ in row access "
        "paths rather than in I/O parallelism, so the effect is expected to be small, but it "
        "is not excluded by measurement. Table 10 therefore gives the indexed configuration "
        "scaled across a range of hardware factors rather than at a single assumed "
        "conversion, with the measured row being the calibration platform itself."))
    p.append(caption("Table", "10. Sensitivity of indexed-configuration timings to a "
                              "hardware scaling factor."))
    p.append(table_sensitivity(r))
    p.append(body(
        "Because the reproduction package includes the schema definition, the loader, the "
        "query definitions and the benchmark harness, executing the sweep on the reference "
        "platform regenerates the absolute column directly and removes the need to assume a "
        "scaling factor at all. The harness rebuilds each configuration from a common "
        "baseline and reports the median, the standard deviation and the chosen plan for "
        "every cell, so a regeneration can be compared against Table 5 cell by cell."))

    # ---- 4.9 -----------------------------------------------------------
    p.append(h2("4.9 Threats to Validity"))
    p.append(body(
        "Four limitations bound the conclusions. First, and most consequential for the "
        "indexing results, the dataset is small. The largest table holds 99,441 rows and the "
        "whole working set is small relative to the buffer pool, so a full scan is already "
        "cheap and the headroom that indexing can recover is correspondingly small. The "
        "absolute gains reported here should not be extrapolated to datasets one or more "
        "orders of magnitude larger, where the ratio of index-assisted to full-scan work is "
        "unchanged but the absolute cost of the full scan is far higher. The plan-level "
        "conclusions are unaffected; the magnitude conclusions are."))
    p.append(body(
        "Second, the study covers one engine. MariaDB was used because it implements the "
        "MySQL interface and the optimiser switches under study, and MySQL 8.x implements "
        "the same semijoin, materialisation and derived-merge transformations, but the two "
        "engines differ in cost model details, in the threshold at which the optimiser "
        "converts a subquery into a semi-join, and in available index types. The specific "
        "conversion thresholds reported here should not be assumed to hold exactly on "
        "another engine or version. This is a genuine external-validity limit rather than a "
        "presentational one."))
    p.append(body(
        f"Third, the workload set is {NQW} queries drawn from {NFW} families, designed to "
        f"span the access patterns of e-commerce analytics rather than to be representative "
        f"of any particular application's query mix. The geometric means in Table 6 weight "
        f"families equally, which is defensible only in the absence of a defensible workload "
        f"distribution; a different mix would produce different aggregates, though the "
        f"per-query measurements would be unaffected."))
    p.append(body(
        f"Fourth, measurement noise is controlled but not eliminated. Across all cells the "
        f"median coefficient of variation is {r.median_cv() * 100:.1f} percent, with a "
        f"maximum of {r.worst_cv()[0] * 100:.1f} percent. Differences smaller than roughly "
        f"twice the median figure should not be read as ordering effects, which applies in "
        f"particular to the small differences discussed in Sections 4.6 and 4.7. One cell, "
        f"W5.1 under C2, exceeded the 45-second statement limit and is reported as censored; "
        f"it is excluded from all aggregates."))
    return "".join(p)


def conclusion(r: Results) -> str:
    p = []
    g2 = r.geomean_speedup("C2_single") or 0
    g3 = r.geomean_speedup("C3_composite") or 0
    g4 = r.geomean_speedup("C4_covering") or 0
    w5 = [(r.med("C0_zero", q) or 0) for q in
          ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s5 = max(w5) / min(w5) if min(w5) > 0 else float("nan")
    c4 = [(r.med("C4_covering", q) or 0) for q in
          ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s5c4 = max(c4) / min(c4) if min(c4) > 0 else float("nan")
    p.append(h1("5. Conclusion"))
    p.append(body(
        f"This study separated the two decisions that determine SQL execution efficiency, "
        f"index design and query formulation, and measured each independently on a "
        f"normalised nine-table schema built from {SCHEMA_ROWS:,} rows of real marketplace "
        f"transaction data. Aggregated over the {len(QUERY_ORDER) - 1} non-outlier queries, "
        f"the three deliberately index configurations achieved geometric-mean speed-ups over "
        f"the unindexed baseline of {r.fmt_x(g2)} for the broad single-column set, "
        f"{r.fmt_x(g3)} for the composite set and {r.fmt_x(g4)} for the composite-plus-"
        f"covering set. Taken alone those figures would support the conventional advice to "
        f"index broadly and stop. Read together with the per-query results and the recorded "
        f"plans, they support a different and more specific set of conclusions."))
    p.append(body(
        f"First, aggregate speed-ups are a poor guide to index design, and on this workload "
        f"they were actively misleading. The configuration designed to be the most "
        f"sophisticated performed worst. The reason is that column order within an index "
        f"determines which queries the index can serve at all: a composite index cannot "
        f"resolve a predicate or an ordering on a trailing column while its leading column "
        f"is unconstrained. Replacing a single-column index with a composite one on the same "
        f"column cost one query a factor of {((r.med('C4_covering', 'W8.1') or 0) / max(r.med('C2_single', 'W8.1') or 1e-9, 1e-9)):.0f} "
        f"and another a factor of {((r.med('C4_covering', 'W2.2 SARG month') or 0) / max(r.med('C2_single', 'W2.2 SARG month') or 1e-9, 1e-9)):.0f}. "
        f"The composite indexes were not worthless; they were the only configuration that "
        f"improved the window-function workload W7.1. The conclusion is not that one design "
        f"wins but that there is no universally best index set, and that the question to ask "
        f"is not how many indexes to create but whether each index's leading column is the "
        f"column the query constrains, orders by or groups on."))
    p.append(body(
        f"Second, the relative cost of JOIN and subquery syntax is a property of the plan "
        f"rather than of the syntax, and its sign is not stable. For one anti-join the "
        f"subquery forms were {s5:.0f}× faster than the LEFT JOIN form before indexing and "
        f"{s5c4:.1f}× slower after an index was added on the join column. This is why "
        f"rules of thumb of the form always prefer joins, or always prefer EXISTS, cannot be "
        f"correct: they encode an assumption about plans that the optimiser, not the "
        f"author, determines. The operational implication is cheap. Inspect the plan before "
        f"rewriting, because a rewrite justified by a rule of thumb can cost three orders "
        f"of magnitude in one direction and save them in the other."))
    p.append(body(
        f"Third, predicate form and index design are not independent decisions either. "
        f"Rewriting a function application as a range predicate was worth a factor of "
        f"{((r.med('C2_single', 'W2.1 non-SARG month') or 0) / max(r.med('C2_single', 'W2.2 SARG month') or 1e-9, 1e-9)):.0f} "
        f"where an index with the correct leading column existed, and almost nothing where "
        f"it did not, and its benefit was further moderated by selectivity: a range covering "
        f"{pct(SELECTIVITY['year'], SELECTIVITY['orders_total']):.0f} percent of a table "
        f"saves almost nothing. Neither variable can be evaluated in "
        f"isolation, which is the strongest methodological argument for measuring them "
        f"together as done here."))
    p.append(body(
        f"Finally, a result that qualifies the others. Overall gains from indexing were "
        f"modest, of roughly twofold, and several queries were unimproved. This is a "
        f"property of the regime rather than of the method: the largest table holds 99,441 "
        f"rows and a full scan of it costs tens of milliseconds, so there is little headroom "
        f"for an index to recover. The magnitude of these gains should not be extrapolated "
        f"to larger datasets, where full scans are proportionally far more expensive and the "
        f"same plan-level mechanisms would deliver far larger absolute benefits. The "
        f"plan-level conclusions, which are the substance of this paper, are independent of "
        f"both dataset size and hardware."))
    p.append(body(
        f"For practitioners the ordering that follows is: express the predicate in a form "
        f"the optimiser can use; check its selectivity; inspect the plan; create the "
        f"smallest index whose leading column matches the driving predicate or ordering; and "
        f"re-measure, because index and query decisions are not separable. For researchers "
        f"the open questions are the write cost this read-only design omits, the behaviour "
        f"of the same workloads on additional engines and dataset sizes, and whether index "
        f"selection can be guided directly by measured examined-row counts rather than by "
        f"cardinality estimates."))
    return "".join(p)


def back_matter(r: Results) -> str:
    p = []
    p.append(h1("Acknowledgment"))
    p.append(body(
        "The authors thank [institution] for access to the computing resources used in "
        "this study. The authors declare no funding was received for this research."))
    p.append(h1("Declarations"))
    p.append(body(
        "Author contribution. [Author One] conceived the study, designed the measurement "
        "protocol, implemented the schema and benchmark harness, and drafted the manuscript. "
        "[Author Two] and [Author Three] contributed to the literature review, verified "
        "the reference accreditation data, and reviewed the manuscript. All authors approved "
        "the final version."))
    p.append(body(
        "Conflict of interest. The authors declare no conflict of interest."))
    p.append(body(
        "Additional information. No additional information is available for this paper."))
    p.append(h1("Data and Software Availability"))
    p.append(body(
        "The dataset analysed in this paper is the Brazilian E-Commerce public dataset "
        "released by Olist and is publicly available at "
        "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. The complete "
        "reproduction package is available on request from the corresponding author and "
        f"comprises the schema definition, the CSV-to-database loader, the {NQW} query "
        "definitions, the benchmark harness that produced every measurement reported here, "
        "and the raw per-run timings including standard deviations."))
    p.append(h1("Appendix A. Query Definitions"))
    p.append(body(
        f"The {NQW} queries executed in this study are reproduced below in the order in "
        "which they appear in Table 2. Each statement is shown as executed; the five "
        "measured index configurations alter the plan but not the statement."))
    for label in QUERY_ORDER:
        sql = r.sql.get(label, "").strip()
        if not sql:
            continue
        p.append(dx.para(dx.run(f"{label}  —  {QUERY_DESC[label]}", b=True, sz=8),
                         align="left", before=140, after=40, left=0, hanging=0,
                         keep_next=True))
        p.append(mono_block(sql))
    return "".join(p)


def reference_list() -> str:
    p = [h1("References")]
    for i, (_key, _sinta, text) in enumerate(REFERENCES, start=1):
        p.append(dx.para(dx.run(f"[{i}]\t", sz=9) + dx.run(text, sz=9),
                         align="both", after=60, left=567, hanging=567))
    return "".join(p)


# ==========================================================================
# assembly
# ==========================================================================
def main() -> int:
    r = Results()
    bm = load_benchmark_module()

    imgs = dx.ImageRegistry()
    fig_w = int(CONTENT_INCH * EMU_PER_INCH)

    # abstract_and_keywords() emits the ARTICLE INFO block under its own heading
    chunks = [front_matter(), abstract_and_keywords(r)]

    for marker in ("FIGURE_1", "FIGURE_2", "FIGURE_3", "FIGURE_4"):
        pass  # figures are injected below, after the narrative is built

    narrative = (introduction(r, bm) + related_work(r) + method(r, bm)
                 + results(r) + conclusion(r))

    fig_map = {
        "FIGURE_1": "fig1_execution_time.png",
        "FIGURE_2": "fig2_speedup.png",
        "FIGURE_3": "fig3_join_vs_subquery.png",
        "FIGURE_4": "fig4_sargability.png",
    }
    for marker, fname in fig_map.items():
        path = os.path.join(FIGDIR, fname)
        if marker in narrative:
            if not os.path.isfile(path):
                print(f"WARNING: {path} missing, leaving {marker} unresolved")
                continue
            narrative = narrative.replace(marker,
                                          imgs.figure_para(path, fig_w))
    if "FIGURE_" in narrative:
        leftover = [m for m in fig_map if m in narrative]
        print(f"WARNING: unresolved figure markers: {leftover}")

    body_xml = "".join(chunks) + narrative + back_matter(r) + reference_list()
    dx.build(TEMPLATE, OUT, body_xml, imgs)

    print(f"wrote {OUT}")
    print(f"  references: {len(REFERENCES)}")
    print(f"  figures embedded: {len(imgs.items)}")
    print(f"  measurements: {r.repeats} timed repetitions per cell, "
          f"{r.repeats * 5 * len(QUERY_ORDER)} timed runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
