#!/usr/bin/env bash
# Stage 2 of the ETL: load the cleaned TSVs produced by 01_extract.py
# into the MySQL-compatible server using plain LOAD DATA (no user variables).
set -euo pipefail

SOCK="${MYSQL_SOCK:-/tmp/opencode/mysql/run/my.sock}"
TSV="${TSV_DIR:?set TSV_DIR}"
SQLDIR="$(cd "$(dirname "$0")" && pwd)"

db() { mariadb --socket="$SOCK" -u root "$@"; }

echo "[1/3] creating baseline schema (primary keys only, no secondary indexes)"
db < "$SQLDIR/01_schema.sql"

# table -> (tsv file, optional trailing WHERE for de-duplication)
load() {
  local table="$1"
  local sql="LOAD DATA LOCAL INFILE '$TSV/$table.tsv'
    INTO TABLE $table
    FIELDS TERMINATED BY '\t' ESCAPED BY '\\\\'
    LINES TERMINATED BY '\n'"
  printf '  -> %-22s' "$table"
  db olist_bp -e "$sql"
  db olist_bp -N -e "SELECT CONCAT('rows=',COUNT(*)) FROM $table;"
}

echo "[2/3] loading"
load customers
load sellers
load products
load category_translation
load orders
load order_items
load order_payments
load order_reviews

# geolocation: 1,000,163 survey points collapse to 19,015 zip prefixes.
# LOAD DATA has no WHERE clause, so stage then insert one row per prefix.
echo "  -> geolocation           (staging + dedup)"
db olist_bp -e "
  DROP TABLE IF EXISTS geolocation_stage;
  CREATE TABLE geolocation_stage LIKE geolocation;"
db olist_bp -e "LOAD DATA LOCAL INFILE '$TSV/geolocation.tsv'
  INTO TABLE geolocation_stage
  FIELDS TERMINATED BY '\t' ESCAPED BY '\\\\'
  LINES TERMINATED BY '\n';"
db olist_bp -e "
  INSERT INTO geolocation
  SELECT geolocation_zip_code_prefix,
         AVG(geolocation_lat),
         AVG(geolocation_lng),
         SUBSTRING_INDEX(GROUP_CONCAT(geolocation_city ORDER BY geolocation_city), ',', 1),
         SUBSTRING_INDEX(GROUP_CONCAT(geolocation_state ORDER BY geolocation_state), ',', 1)
  FROM geolocation_stage
  GROUP BY geolocation_zip_code_prefix;
  DROP TABLE geolocation_stage;"
db olist_bp -N -e "SELECT CONCAT('rows=',COUNT(*)) FROM geolocation;"

echo "[3/3] ANALYZE TABLE (refresh optimiser statistics)"
db olist_bp -e "ANALYZE TABLE customers, sellers, products, category_translation,
  orders, order_items, order_payments, order_reviews, geolocation;" > /dev/null

echo
echo "final row counts:"
db olist_bp -N -e "
SELECT 'customers',COUNT(*) FROM customers UNION ALL
SELECT 'sellers',COUNT(*) FROM sellers UNION ALL
SELECT 'products',COUNT(*) FROM products UNION ALL
SELECT 'category_translation',COUNT(*) FROM category_translation UNION ALL
SELECT 'orders',COUNT(*) FROM orders UNION ALL
SELECT 'order_items',COUNT(*) FROM order_items UNION ALL
SELECT 'order_payments',COUNT(*) FROM order_payments UNION ALL
SELECT 'order_reviews',COUNT(*) FROM order_reviews UNION ALL
SELECT 'geolocation',COUNT(*) FROM geolocation;"