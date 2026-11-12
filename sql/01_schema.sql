-- ============================================================
-- Olist Brazilian E-Commerce: relational schema (baseline, no secondary indexes)
-- Engine: InnoDB, utf8mb4
-- ============================================================

DROP DATABASE IF EXISTS olist_bp;
CREATE DATABASE olist_bp CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE olist_bp;

CREATE TABLE customers (
  customer_id          CHAR(32)    NOT NULL,
  customer_unique_id   CHAR(32)    NOT NULL,
  customer_zip_code_prefix CHAR(5)   NOT NULL,
  customer_city         VARCHAR(40) NOT NULL,
  customer_state        CHAR(2)     NOT NULL,
  PRIMARY KEY (customer_id)
) ENGINE=InnoDB;

CREATE TABLE sellers (
  seller_id            CHAR(32)    NOT NULL,
  seller_zip_code_prefix CHAR(5)    NOT NULL,
  seller_city          VARCHAR(40) NOT NULL,
  seller_state         CHAR(2)     NOT NULL,
  PRIMARY KEY (seller_id)
) ENGINE=InnoDB;

CREATE TABLE products (
  product_id           CHAR(32)    NOT NULL,
  product_category_name VARCHAR(60) DEFAULT NULL,
  product_name_length  SMALLINT     DEFAULT NULL,
  product_desc_length  SMALLINT     DEFAULT NULL,
  product_photos_qty   TINYINT      DEFAULT NULL,
  product_weight_g     INT          DEFAULT NULL,
  product_length_cm    SMALLINT     DEFAULT NULL,
  product_height_cm    SMALLINT     DEFAULT NULL,
  product_width_cm     SMALLINT     DEFAULT NULL,
  PRIMARY KEY (product_id)
) ENGINE=InnoDB;

CREATE TABLE category_translation (
  product_category_name        VARCHAR(60) NOT NULL,
  product_category_name_english VARCHAR(60) NOT NULL,
  PRIMARY KEY (product_category_name)
) ENGINE=InnoDB;

CREATE TABLE orders (
  order_id                 CHAR(32)    NOT NULL,
  customer_id              CHAR(32)    NOT NULL,
  order_status             VARCHAR(25) NOT NULL,
  order_purchase_timestamp DATETIME    NOT NULL,
  order_approved_at        DATETIME     DEFAULT NULL,
  order_delivered_carrier_date DATETIME DEFAULT NULL,
  order_delivered_customer_date DATETIME DEFAULT NULL,
  order_estimated_delivery_date  DATETIME DEFAULT NULL,
  PRIMARY KEY (order_id),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB;

CREATE TABLE order_items (
  order_id            CHAR(32)     NOT NULL,
  order_item_id       INT          NOT NULL,
  product_id          CHAR(32)     NOT NULL,
  seller_id           CHAR(32)     NOT NULL,
  shipping_limit_date DATETIME     NOT NULL,
  price               DECIMAL(10,2) NOT NULL,
  freight_value       DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (order_id, order_item_id),
  CONSTRAINT fk_items_order   FOREIGN KEY (order_id) REFERENCES orders(order_id),
  CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products(product_id),
  CONSTRAINT fk_items_seller  FOREIGN KEY (seller_id)  REFERENCES sellers(seller_id)
) ENGINE=InnoDB;

CREATE TABLE order_payments (
  order_id           CHAR(32)      NOT NULL,
  payment_sequential INT           NOT NULL,
  payment_type       VARCHAR(25)   NOT NULL,
  payment_installments TINYINT     NOT NULL,
  payment_value      DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (order_id, payment_sequential),
  CONSTRAINT fk_pay_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB;

-- The released dataset contains 814 duplicate review_id values across different
-- orders, so review_id alone is not unique; the composite key preserves every
-- source row without inventing data, and keeps the clustered index prefix on
-- review_id.
CREATE TABLE order_reviews (
  review_id           CHAR(32) NOT NULL,
  order_id            CHAR(32) NOT NULL,
  review_score        TINYINT DEFAULT NULL,
  review_comment_title  TEXT,
  review_comment_message TEXT,
  review_creation_date   DATETIME DEFAULT NULL,
  review_answer_timestamp DATETIME DEFAULT NULL,
  PRIMARY KEY (review_id, order_id)
) ENGINE=InnoDB;

-- geolocation has one row per survey point (1,000,163 rows) but only 19,015
-- distinct zip prefixes; one representative row per prefix is retained, which
-- is what downstream analytics actually consume.
CREATE TABLE geolocation (
  geolocation_zip_code_prefix CHAR(5)    NOT NULL,
  geolocation_lat  DOUBLE NOT NULL,
  geolocation_lng  DOUBLE NOT NULL,
  geolocation_city VARCHAR(60) NOT NULL,
  geolocation_state CHAR(2)  NOT NULL,
  PRIMARY KEY (geolocation_zip_code_prefix)
) ENGINE=InnoDB;