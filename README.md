# Reproduction package — SQL query efficiency on the Olist dataset

Code, data and raw timings for:

> **Comparative Analysis of SQL Query Execution Efficiency Using Indexing, JOIN,
> and Subquery Optimization on the Olist Brazilian E-Commerce Dataset**
> Rizky Parlika, Mohammad Yuan Setiawan, Nabil Faruq Shalahuddin,
> Mochamad Ghifari Rasyad
> *Information Technology International Journal (ITIJ)*

The study crosses **five index configurations** with **eighteen queries** on a
nine-table InnoDB schema (569,774 rows) and records, for every cell, the median
of 12 timed repetitions together with the execution plan the optimiser chose.

## What is here

| Path | Purpose |
|---|---|
| `sql/01_extract.py` | Olist CSV → clean TSV (RFC 4180 parsing, NULL handling, dedup reporting) |
| `sql/01_schema.sql` | Nine-table normalised InnoDB schema, primary keys only |
| `sql/02_load.sh` | Creates the schema and loads the TSVs; prints row counts |
| `benchmark.py` | The measurement harness: 5 index configurations × 18 queries |
| `summary.py` | Derived statistics (medians, dispersion, speed-ups, geometric means) |
| `make_figures.py` | Renders the four figures from `results/results.json` |
| `svg_figures.py` | Same four figures as vector SVG |
| `raster.py` | Dependency-free PNG writer and bar-chart renderer |
| `docx_writer.py` | WordprocessingML helpers used to assemble the manuscript |
| `references.py` | The 28-entry reference list with SINTA/Scopus annotations |
| `results/results.json` | Raw measurements: every repetition, plus EXPLAIN output |
| `results/results.csv` | Flat per-cell summary |
| `figure_data/*.csv` | The numbers plotted in each figure |
| `figures/*.png` | The four rendered figures (raster) |
| `figures_svg/*.svg` | The four rendered figures (vector) |

## Requirements

* Python 3.11 or newer — **standard library only**, no `pip install` needed
* A MySQL-compatible server with a client on `PATH` as `mariadb` or `mysql`
* The Olist dataset from
  <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>

## Reproducing the measurements

```bash
# 1. Point the scripts at your server socket and the CSV directory
export MYSQL_SOCK=/var/run/mysqld/mysqld.sock   # or /tmp/mysql.sock
export DATA_DIR=/path/to/brazilian-ecommerce

# 2. Load the data (prints row counts; compare against Table 1 of the paper)
python3 sql/01_extract.py "$DATA_DIR" /tmp/olist_tsv
TSV_DIR=/tmp/olist_tsv bash sql/02_load.sh

# 3. Run the sweep: 5 configurations x 18 queries x 12 timed repetitions
python3 benchmark.py --repeats 12 --warmup 3 --out results

# 4. Regenerate figures and the manuscript
python3 make_figures.py
python3 build_paper.py
```

The sweep takes about 31 minutes on the reference machine, dominated by the
`W5.1 LEFT JOIN` query, which costs roughly 18 s per execution in the four
configurations that lack an index on `order_reviews.order_id`.

## Notes on the measurement design

* **Timing source.** Elapsed time comes from the server's own statement profiler
  (`SET profiling=1` … `SHOW PROFILES`), not client-side wall-clock timing, so
  connection handling and result serialisation are excluded.
* **Statistics.** Three untimed warm-ups, then 12 timed repetitions. The median
  is the reported statistic; mean, standard deviation, min and max are all kept
  in `results.json`.
* **Censoring.** `max_statement_time` is set to 45 s. One cell — `W5.1 LEFT JOIN`
  under configuration C2 — exceeds it and is recorded as censored. It is
  excluded from every aggregate and reported as `> 45 s`.
* **The outlier.** `W5.1` is excluded from all totals and geometric means
  because its magnitude would dominate them. It is analysed on its own in
  Section 4.4 of the paper, where it is the principal result.
* **Plans.** Every query is additionally run under `EXPLAIN` and under
  actual-row-count instrumentation, so each timing is attributable to a chosen
  access path rather than inferred from it.
* **Engine.** The measurements were taken on MariaDB 10.11.6, which implements
  the MySQL interface and the optimiser switches under study.

## Re-running on your own machine

The harness is deterministic in its configuration sequence: each configuration
is rebuilt from a common baseline by `reset_schema()`, so configurations never
inherit indexes they did not declare. After running the sweep on your machine,
compare `results/results.json` against the copy here cell by cell. Expect the
**plan-level** results (which access path is chosen for each query) to be
identical and the **absolute timings** to differ. Speed-up ratios should be
broadly preserved, because a speed-up is governed by the ratio of rows examined
to rows returned, which is a property of the data and the access path rather
than of the processor.

## License

Code: MIT. The Olist dataset is distributed under its own terms on Kaggle and is
not redistributed here.
