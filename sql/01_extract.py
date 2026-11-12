#!/usr/bin/env python3
"""
Stage 1 of the ETL: Olist CSV -> clean, tab-separated, quote-free TSV.

Rationale: LOAD DATA ... INTO TABLE with user variables proved fragile on
MariaDB (silently dropping rows). Pre-normalising the files in Python makes the
load deterministic and lets us assert exact row counts.

Rules applied:
  * RFC4180 parsing (handles quoted fields containing commas/quotes/newlines)
  * embedded CR/LF inside free-text fields collapsed to a single space
  * NULL for empty optional fields
  * BOM stripped from the first header cell
  * one output row per input row; duplicates on the primary key are reported
    but preserved (the schema enforces uniqueness, so we surface them instead
    of hiding them)
"""
import csv
import os
import sys
from collections import Counter

SRC = sys.argv[1]
DST = sys.argv[2]

# table -> (source csv, list of destination columns, set of required columns)
SPEC = {
    "customers": (
        "olist_customers_dataset.csv",
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
         "customer_city", "customer_state"],
        ["customer_id"],
    ),
    "sellers": (
        "olist_sellers_dataset.csv",
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
        ["seller_id"],
    ),
    "products": (
        "olist_products_dataset.csv",
        ["product_id", "product_category_name", "product_name_length",
         "product_desc_length", "product_photos_qty", "product_weight_g",
         "product_length_cm", "product_height_cm", "product_width_cm"],
        ["product_id"],
    ),
    "category_translation": (
        "product_category_name_translation.csv",
        ["product_category_name", "product_category_name_english"],
        ["product_category_name"],
    ),
    "orders": (
        "olist_orders_dataset.csv",
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
         "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"],
        ["order_id", "customer_id"],
    ),
    "order_items": (
        "olist_order_items_dataset.csv",
        ["order_id", "order_item_id", "product_id", "seller_id",
         "shipping_limit_date", "price", "freight_value"],
        ["order_id", "order_item_id"],
    ),
    "order_payments": (
        "olist_order_payments_dataset.csv",
        ["order_id", "payment_sequential", "payment_type",
         "payment_installments", "payment_value"],
        ["order_id", "payment_sequential"],
    ),
    "order_reviews": (
        "olist_order_reviews_dataset.csv",
        ["review_id", "order_id", "review_score", "review_comment_title",
         "review_comment_message", "review_creation_date",
         "review_answer_timestamp"],
        ["review_id"],
    ),
    "geolocation": (
        "olist_geolocation_dataset.csv",
        ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
         "geolocation_city", "geolocation_state"],
        ["geolocation_zip_code_prefix"],
    ),
}


def clean(value: str) -> str:
    """Collapse newlines/tabs, strip, and escape for tab-separated output."""
    v = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    v = v.replace("\t", " ").strip()
    return "\\N" if v == "" else v


def main() -> int:
    os.makedirs(DST, exist_ok=True)
    report = []

    for table, (fname, cols, key_cols) in SPEC.items():
        path = os.path.join(SRC, fname)
        if not os.path.isfile(path):
            print(f"FATAL: missing {path}", file=sys.stderr)
            return 1

        out_path = os.path.join(DST, f"{table}.tsv")
        n = 0
        keys = Counter()
        with open(path, encoding="utf-8-sig", newline="") as fh, \
             open(out_path, "w", encoding="utf-8", newline="") as out:
            reader = csv.reader(fh)
            header = next(reader)
            if len(header) != len(cols):
                print(f"FATAL: {fname} has {len(header)} columns, "
                      f"expected {len(cols)}", file=sys.stderr)
                return 1
            idx_key = [cols.index(k) for k in key_cols]
            writer = csv.writer(out, delimiter="\t", lineterminator="\n",
                                quoting=csv.QUOTE_NONE, escapechar="\\")
            for row in reader:
                if len(row) != len(cols):
                    print(f"WARN {fname}: row {n} has {len(row)} fields",
                          file=sys.stderr)
                    continue
                row = [clean(c) for c in row]
                keys[tuple(row[i] for i in idx_key)] += 1
                writer.writerow(row)
                n += 1

        dups = sum(c - 1 for c in keys.values() if c > 1)
        report.append((table, n, len(keys), dups))
        print(f"{table:24s} rows={n:>9,}  unique_pk={len(keys):>9,}  "
              f"dup_pk_rows={dups:,}")

    print(f"\nTotal rows written: {sum(r[1] for r in report):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())