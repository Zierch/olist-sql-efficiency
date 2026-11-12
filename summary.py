"""
Quantitative summary of the measured sweep: turns results.json into the
derived quantities the paper reports (medians, dispersion, speedups, geometric
means, per-family aggregates).
"""
from __future__ import annotations

import json
import math
import os
import statistics

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "results.json")

CONFIG_ORDER = ["C0_zero", "C1_fk", "C2_single", "C3_composite", "C4_covering"]
CONFIG_SHORT = {
    "C0_zero": "C0",
    "C1_fk": "C1",
    "C2_single": "C2",
    "C3_composite": "C3",
    "C4_covering": "C4",
}
CONFIG_DESC = {
    "C0_zero": "No secondary index (primary keys only, foreign keys removed)",
    "C1_fk": "Foreign-key indexes only (post-import baseline)",
    "C2_single": "FK + single-column indexes on filter and join columns",
    "C3_composite": "FK + composite indexes (equality, range)",
    "C4_covering": "FK + composite + covering indexes",
}

QUERY_ORDER = [
    "W1.1", "W1.2", "W1.3",
    "W2.1 non-SARG month", "W2.2 SARG month",
    "W2.3 non-SARG year", "W2.4 SARG year",
    "W3.1",
    "W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS",
    "W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS",
    "W6.1 flat JOIN", "W6.2 derived table",
    "W7.1", "W8.1",
]

QUERY_DESC = {
    "W1.1": "Count of orders with a given status",
    "W1.2": "Revenue per order status via correlated payment roll-up",
    "W1.3": "Customer count per state",
    "W2.1 non-SARG month": "June 2018 orders via DATE_FORMAT() on the column",
    "W2.2 SARG month": "June 2018 orders via a half-open range on the column",
    "W2.3 non-SARG year": "2018 orders via YEAR() on the column",
    "W2.4 SARG year": "2018 orders via a half-open range on the column",
    "W3.1": "Delivered orders per customer state (two-table equi-join)",
    "W4.1 JOIN": "Orders of customers in one state, INNER JOIN form",
    "W4.2 IN": "Same result, uncorrelated IN subquery",
    "W4.3 EXISTS": "Same result, correlated EXISTS subquery",
    "W5.1 LEFT JOIN": "Unrated orders in a 14-day window, LEFT JOIN ... IS NULL",
    "W5.2 NOT IN": "Same result, uncorrelated NOT IN subquery",
    "W5.3 NOT EXISTS": "Same result, correlated NOT EXISTS subquery",
    "W6.1 flat JOIN": "Monthly revenue per state, flat four-table join",
    "W6.2 derived table": "Same result, join hoisted into a derived table",
    "W7.1": "Top-3 sellers per state via RANK() window function",
    "W8.1": "Twenty most recent orders, ORDER BY ... LIMIT",
}

# Rows matched by the SARGability workload, measured directly against the loaded
# schema. Both members of each pair were verified to return identical counts, and
# the function form was verified to agree with the range form.
SELECTIVITY = {
    "month": 6_167,      # order_purchase_timestamp in [2018-06-01, 2018-07-01)
    "year": 54_011,      # order_purchase_timestamp in [2018-01-01, 2019-01-01)
    "orders_total": 99_441,
}


def pct(n: int, of: int) -> float:
    return 100.0 * n / of


FAMILY_OF = {
    "W1.1": "W1", "W1.2": "W1", "W1.3": "W1",
    "W2.1 non-SARG month": "W2a", "W2.2 SARG month": "W2a",
    "W2.3 non-SARG year": "W2b", "W2.4 SARG year": "W2b",
    "W3.1": "W3",
    "W4.1 JOIN": "W4", "W4.2 IN": "W4", "W4.3 EXISTS": "W4",
    "W5.1 LEFT JOIN": "W5", "W5.2 NOT IN": "W5", "W5.3 NOT EXISTS": "W5",
    "W6.1 flat JOIN": "W6", "W6.2 derived table": "W6",
    "W7.1": "W7", "W8.1": "W8",
}

FAMILIES = {
    "W1": "Single-table filter and aggregation",
    "W2a": "Predicate form, selective month",
    "W2b": "Predicate form, non-selective year",
    "W3": "Two-table INNER JOIN",
    "W4": "Semi-join formulation",
    "W5": "Anti-join formulation",
    "W6": "Multi-table analytical aggregation",
    "W7": "Window-function ranking",
    "W8": "ORDER BY with LIMIT",
}


class Results:
    def __init__(self, path: str = RESULTS):
        with open(path) as fh:
            blob = json.load(fh)
        self.repeats = blob.get("repeats")
        self.warmup = blob.get("warmup")
        self.median: dict[tuple[str, str], float] = {}
        self.mean: dict[tuple[str, str], float] = {}
        self.stdev: dict[tuple[str, str], float] = {}
        self.rows: dict[tuple[str, str], int] = {}
        self.explain: dict[tuple[str, str], str] = {}
        self.sql: dict[str, str] = {}
        self.note: dict[str, str] = {}
        self.group: dict[str, str] = {}
        # cells that exceeded the per-statement time limit: a lower bound only
        self.censored_ms: dict[tuple[str, str], float] = {}
        self.errors: dict[tuple[str, str], str] = {}
        for rec in blob["results"]:
            key = (rec["phase"], rec["label"])
            self.sql.setdefault(rec["label"], rec.get("sql", ""))
            self.note[rec["label"]] = rec.get("note", "")
            self.group[rec["label"]] = rec.get("group", "")
            if rec.get("error") == "timeout" or rec.get("censored"):
                self.censored_ms[key] = float(rec.get("median_ms") or 45_000.0)
                continue
            if rec.get("error"):
                # the server aborts a statement that exceeds max_statement_time,
                # which surfaces as an ordinary SQL error rather than a flag
                if "max_statement_time" in str(rec["error"]):
                    self.censored_ms[key] = 45_000.0
                else:
                    self.errors[key] = str(rec["error"])[:120]
                continue
            if rec.get("median_ms") is None:
                continue
            self.median[key] = float(rec["median_ms"])
            self.mean[key] = float(rec.get("mean_ms", 0.0))
            self.stdev[key] = float(rec.get("stdev_ms", 0.0))
            self.rows[key] = int(rec.get("rows_returned") or 0)
            self.explain[key] = rec.get("explain", "")

    def med(self, cfg: str, q: str) -> float | None:
        return self.median.get((cfg, q))

    def is_censored(self, cfg: str, q: str) -> bool:
        return (cfg, q) in self.censored_ms

    def cell_text(self, cfg: str, q: str, censored_note: str = "> limit") -> str:
        """Rendered value for a table cell, flagging censored measurements."""
        if self.is_censored(cfg, q):
            return censored_note
        v = self.med(cfg, q)
        return self.fmt_ms(v) if v is not None else "n/a"

    def speedup(self, cfg: str, q: str) -> float | None:
        base, cur = self.med("C0_zero", q), self.med(cfg, q)
        if not base or cur is None:
            return None
        return base / cur

    # W5.1 is excluded from every aggregate: it is three orders of magnitude
    # larger than any other cell and is censored in one configuration, so
    # including it inconsistently would make cross-configuration means
    # incomparable. It is analysed on its own in the anti-join analysis.
    OUTLIER = ("W5.1 LEFT JOIN",)

    def geomean_speedup(self, cfg: str, queries: list[str] | None = None,
                        exclude: tuple[str, ...] | None = None) -> float | None:
        qs = queries or QUERY_ORDER
        if exclude is None:
            exclude = self.OUTLIER
        ratios = [self.speedup(cfg, q) for q in qs if q not in exclude]
        ratios = [r for r in ratios if r and r > 0]
        if not ratios:
            return None
        return math.exp(sum(math.log(r) for r in ratios) / len(ratios))

    def family_geomean_speedup(self, cfg: str, family: str,
                              exclude: tuple[str, ...] | None = None) -> float | None:
        qs = [q for q in QUERY_ORDER if FAMILY_OF[q] == family]
        return self.geomean_speedup(cfg, qs, exclude)

    def cvs(self) -> list[float]:
        """Coefficient of variation per cell, as standard deviation over mean.

        The standard definition is used rather than deviation about the median so
        that the figure matches what a reader would compute from the raw runs.
        """
        out = []
        for key, mean in self.mean.items():
            if mean and mean > 0:
                out.append(self.stdev.get(key, 0.0) / mean)
        return sorted(out)

    def worst_cv(self) -> tuple[float, str, str]:
        """Largest coefficient of variation across all (config, query) cells."""
        worst = (0.0, "", "")
        for (cfg, q), mean in self.mean.items():
            if not mean or mean <= 0:
                continue
            cv = self.stdev.get((cfg, q), 0.0) / mean
            if cv > worst[0]:
                worst = (cv, cfg, q)
        return worst

    def median_cv(self) -> float:
        cvs = self.cvs()
        return cvs[len(cvs) // 2] if cvs else 0.0

    def total(self, cfg: str, exclude: tuple[str, ...] | None = None) -> float | None:
        """Total sweep time. W5.1 is excluded because it is censored in one
        configuration and three orders of magnitude larger than anything else,
        so including it would make the total uninformative."""
        if exclude is None:
            exclude = self.OUTLIER
        vals = [self.med(cfg, q) for q in QUERY_ORDER if q not in exclude]
        vals = [v for v in vals if v is not None]
        return sum(vals) if vals else None

    def fmt_ms(self, v: float | None, dp: int = 2) -> str:
        if v is None:
            return "n/a"
        if v >= 1000:
            return f"{v/1000:.2f} s"
        return f"{v:.{dp}f}"

    def fmt_ms_u(self, v: float | None) -> str:
        """Median time with an explicit unit, for use in prose."""
        if v is None:
            return "not measured"
        if v >= 1000:
            return f"{v / 1000:.2f} s"
        return f"{v:.2f} ms"

    def fmt_x(self, v: float | None) -> str:
        if v is None:
            return "n/a"
        if v >= 100:
            return f"{v:.0f}x"
        if v >= 10:
            return f"{v:.1f}x"
        return f"{v:.2f}x"

    def plan_summary(self, cfg: str, q: str) -> str:
        """Condense an EXPLAIN tab-separated block into a short plan string."""
        raw = self.explain.get((cfg, q), "")
        if not raw:
            return ""
        parts = []
        for line in raw.strip().splitlines():
            f = line.split("\t")
            if len(f) < 10:
                continue
            # id, select_type, table, type, possible_keys, key, key_len,
            # ref, rows, Extra
            tbl, typ, key, extra = f[2], f[3], f[5], f[9]
            access = {"ALL": "scan", "index": "idx-scan", "range": "range",
                      "ref": "ref", "eq_ref": "eq_ref", "const": "const"}.get(typ, typ)
            parts.append(f"{tbl}:{access}" + (f"[{key}]" if key not in ("NULL", "") else ""))
            if extra and extra not in ("", "Using where"):
                parts[-1] += f"({extra})"
        return "; ".join(parts)