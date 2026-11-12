#!/usr/bin/env python3
"""
Render the paper's figures from results.json using the dependency-free
raster/chart toolkit in raster.py.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raster  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "results.json")
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")

# Query label -> short two-line axis label. The full SQL text lives in the
# paper's workload table, so the figures only need a scannable handle.
SHORT: dict[str, str] = {
    "W1.1": "W1.1",
    "W1.2": "W1.2",
    "W1.3": "W1.3",
    "W2.1 non-SARG month": "W2.1\nnon-SARG\nmonth",
    "W2.2 SARG month": "W2.2\nSARG\nmonth",
    "W2.3 non-SARG year": "W2.3\nnon-SARG\nyear",
    "W2.4 SARG year": "W2.4\nSARG\nyear",
    "W3.1": "W3.1",
    "W4.1 JOIN": "W4.1\nJOIN",
    "W4.2 IN": "W4.2\nIN",
    "W4.3 EXISTS": "W4.3\nEXISTS",
    "W5.1 LEFT JOIN": "W5.1\nLEFT JOIN",
    "W5.2 NOT IN": "W5.2\nNOT IN",
    "W5.3 NOT EXISTS": "W5.3\nNOT EX",
    "W6.1 flat JOIN": "W6.1\nflat JOIN",
    "W6.2 derived table": "W6.2\nderived",
    "W7.1": "W7.1",
    "W8.1": "W8.1",
}

QUERY_ORDER = list(SHORT.keys())

CONFIG_ORDER = ["C0_zero", "C1_fk", "C2_single", "C3_composite", "C4_covering"]
CONFIG_LEGEND = ["C0 no index", "C1 FK only", "C2 single-col",
                 "C3 composite", "C4 covering"]


def load() -> dict[tuple[str, str], float]:
    with open(RESULTS) as fh:
        blob = json.load(fh)
    out: dict[tuple[str, str], float] = {}
    for rec in blob["results"]:
        if rec.get("median_ms") is None:
            continue
        out[(rec["phase"], rec["label"])] = float(rec["median_ms"])
    cens = {}
    for rec in blob["results"]:
        err = str(rec.get("error") or "")
        if rec.get("censored") or rec.get("error") == "timeout" \
                or "max_statement_time" in err:
            cens[(rec["phase"], rec["label"])] = CENSOR_LIMIT_MS
    out["_censored"] = cens
    return out


def series_for(data, queries, configs) -> list[list[float | None]]:
    return [[data.get((cfg, q)) for q in queries] for cfg in configs]


CENSOR_LIMIT_MS = 45_000.0


def censored_series(data, queries, configs) -> tuple[list[list[float | None]],
                                                      list[list[bool]]]:
    """Values with censored cells replaced by their lower bound, plus the mask."""
    vals, mask = [], []
    for cfg in configs:
        row, mrow = [], []
        for q in queries:
            if (cfg, q) in data.get("_censored", {}):
                row.append(CENSOR_LIMIT_MS)
                mrow.append(True)
            else:
                row.append(data.get((cfg, q)))
                mrow.append(False)
        vals.append(row)
        mask.append(mrow)
    return vals, mask


def main() -> int:
    os.makedirs(OUTDIR, exist_ok=True)
    data = load()
    missing = [(c, q) for c in CONFIG_ORDER for q in QUERY_ORDER
               if (c, q) not in data]
    if missing:
        print(f"WARNING: {len(missing)} (config, query) cells missing, "
              f"e.g. {missing[:4]}", file=sys.stderr)

    groups = [SHORT[q] for q in QUERY_ORDER]

    # Figure 1 - median execution time for every workload and configuration
    raster.grouped_bar_chart(
        os.path.join(OUTDIR, "fig1_execution_time.png"),
        groups, CONFIG_LEGEND, censored_series(data, QUERY_ORDER, CONFIG_ORDER)[0],
        censored=censored_series(data, QUERY_ORDER, CONFIG_ORDER)[1],
        title="Median server-side execution time by workload and index configuration",
        ylabel="Execution time (ms, log scale)", xlabel="Query workload",
        log_y=True, width=2400, height=1150)

    # Figure 2 - speedup relative to the unindexed baseline
    configs = CONFIG_ORDER[1:]
    speed = []
    for cfg in configs:
        row = []
        for q in QUERY_ORDER:
            base, cur = data.get(("C0_zero", q)), data.get((cfg, q))
            row.append(round(cur / base, 2) if base and cur else None)
        speed.append(row)
    raster.grouped_bar_chart(
        os.path.join(OUTDIR, "fig2_speedup.png"),
        groups, CONFIG_LEGEND[1:], speed,
        title="Execution-time speedup relative to the unindexed baseline (C0)",
        ylabel="Speedup (x, log scale)", xlabel="Query workload",
        log_y=True, width=2400, height=1150)

    # Figure 3 - join formulation families
    fam = ["W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS",
           "W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS"]
    raster.grouped_bar_chart(
        os.path.join(OUTDIR, "fig3_join_vs_subquery.png"),
        [SHORT[k] for k in fam], CONFIG_LEGEND, series_for(data, fam, CONFIG_ORDER),
        title="Semi-join and anti-join formulation compared under identical index configurations",
        ylabel="Execution time (ms, log scale)", xlabel="Query formulation",
        log_y=True, width=2000, height=1120)

    # Figure 4 - predicate form and ORDER BY + LIMIT
    sarg = ["W2.1 non-SARG month", "W2.2 SARG month",
            "W2.3 non-SARG year", "W2.4 SARG year"]
    raster.grouped_bar_chart(
        os.path.join(OUTDIR, "fig4_sargability.png"),
        [SHORT[k] for k in sarg], CONFIG_LEGEND, series_for(data, sarg, CONFIG_ORDER),
        title="Predicate form at two levels of selectivity: selective month versus non-selective year",
        ylabel="Execution time (ms, log scale)", xlabel="Query workload",
        log_y=True, width=1900, height=1120)

    for f in sorted(os.listdir(OUTDIR)):
        print("wrote", os.path.join(OUTDIR, f))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())