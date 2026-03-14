-- =============================================================
-- Costly — Snowflake Demo Data Generator
-- Run this against your trial account to populate ACCOUNT_USAGE
-- with realistic data across multiple warehouses, users, and
-- query patterns. After ~45 min latency everything shows up.
--
-- HOW TO USE:
-- 1. Paste into a Snowflake worksheet as ACCOUNTADMIN
-- 2. Run section by section (each -- SECTION comment is a step)
-- 3. Wait 45 min then connect Costly
-- =============================================================

USE ROLE ACCOUNTADMIN;

-- =============================================================
-- SECTION 1: Create warehouses (simulates different teams)
-- =============================================================

CREATE WAREHOUSE IF NOT EXISTS ANALYTICS_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  COMMENT = 'Analytics team warehouse';

CREATE WAREHOUSE IF NOT EXISTS ETL_WH
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  COMMENT = 'ETL pipeline warehouse';

CREATE WAREHOUSE IF NOT EXISTS REPORTING_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  COMMENT = 'BI reporting warehouse';

CREATE WAREHOUSE IF NOT EXISTS DEV_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  COMMENT = 'Development warehouse';

-- =============================================================
-- SECTION 2: Create roles and users (simulates a real team)
-- =============================================================

CREATE ROLE IF NOT EXISTS ANALYST_ROLE;
CREATE ROLE IF NOT EXISTS ETL_ROLE;
CREATE ROLE IF NOT EXISTS REPORTING_ROLE;

-- Grant roles
GRANT ROLE ANALYST_ROLE TO ROLE SYSADMIN;
GRANT ROLE ETL_ROLE TO ROLE SYSADMIN;
GRANT ROLE REPORTING_ROLE TO ROLE SYSADMIN;

-- Grant warehouse access
GRANT USAGE ON WAREHOUSE ANALYTICS_WH TO ROLE ANALYST_ROLE;
GRANT USAGE ON WAREHOUSE ETL_WH TO ROLE ETL_ROLE;
GRANT USAGE ON WAREHOUSE REPORTING_WH TO ROLE REPORTING_ROLE;
GRANT USAGE ON WAREHOUSE DEV_WH TO ROLE ANALYST_ROLE;
GRANT USAGE ON WAREHOUSE DEV_WH TO ROLE ETL_ROLE;

-- Grant sample data access
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_SAMPLE_DATA TO ROLE ANALYST_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_SAMPLE_DATA TO ROLE ETL_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_SAMPLE_DATA TO ROLE REPORTING_ROLE;

-- =============================================================
-- SECTION 3: Create a demo database and tables (for storage metrics)
-- =============================================================

CREATE DATABASE IF NOT EXISTS COSTLY_DEMO;
CREATE SCHEMA IF NOT EXISTS COSTLY_DEMO.SALES;
CREATE SCHEMA IF NOT EXISTS COSTLY_DEMO.MARKETING;
CREATE SCHEMA IF NOT EXISTS COSTLY_DEMO.FINANCE;
CREATE SCHEMA IF NOT EXISTS COSTLY_DEMO.RAW;

USE DATABASE COSTLY_DEMO;

-- Create tables from sample data (generates real storage)
CREATE OR REPLACE TABLE COSTLY_DEMO.SALES.ORDERS AS
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.ORDERS;

CREATE OR REPLACE TABLE COSTLY_DEMO.SALES.LINEITEMS AS
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.LINEITEM;

CREATE OR REPLACE TABLE COSTLY_DEMO.SALES.CUSTOMERS AS
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.CUSTOMER;

CREATE OR REPLACE TABLE COSTLY_DEMO.MARKETING.WEBSITE_EVENTS AS
SELECT
    SEQ8() AS event_id,
    UNIFORM(1, 10000, RANDOM()) AS user_id,
    ARRAY_CONSTRUCT('page_view','click','purchase','signup','logout')[UNIFORM(0,4,RANDOM())]::STRING AS event_type,
    DATEADD('second', UNIFORM(-7776000, 0, RANDOM()), CURRENT_TIMESTAMP()) AS event_time,
    ARRAY_CONSTRUCT('home','pricing','docs','dashboard','login')[UNIFORM(0,4,RANDOM())]::STRING AS page,
    UNIFORM(0, 500, RANDOM()) / 100.0 AS revenue
FROM TABLE(GENERATOR(ROWCOUNT => 1000000));

CREATE OR REPLACE TABLE COSTLY_DEMO.FINANCE.DAILY_SPEND AS
SELECT
    DATEADD('day', -SEQ4(), CURRENT_DATE()) AS spend_date,
    UNIFORM(5000, 50000, RANDOM()) AS total_spend,
    UNIFORM(3000, 30000, RANDOM()) AS compute_spend,
    UNIFORM(500, 5000, RANDOM()) AS storage_spend,
    UNIFORM(200, 2000, RANDOM()) AS data_transfer_spend
FROM TABLE(GENERATOR(ROWCOUNT => 365));

-- Old table nobody queries (for "stale table" insight)
CREATE OR REPLACE TABLE COSTLY_DEMO.RAW.LEGACY_EVENTS AS
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 100000;

CREATE OR REPLACE TABLE COSTLY_DEMO.RAW.TEMP_STAGING AS
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.LINEITEM LIMIT 500000;

-- =============================================================
-- SECTION 3b: Grant privileges on COSTLY_DEMO to all roles
-- (Must be done as ACCOUNTADMIN before switching roles)
-- =============================================================

USE ROLE ACCOUNTADMIN;

GRANT USAGE ON DATABASE COSTLY_DEMO TO ROLE ANALYST_ROLE;
GRANT USAGE ON DATABASE COSTLY_DEMO TO ROLE ETL_ROLE;
GRANT USAGE ON DATABASE COSTLY_DEMO TO ROLE REPORTING_ROLE;

GRANT USAGE ON ALL SCHEMAS IN DATABASE COSTLY_DEMO TO ROLE ANALYST_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE COSTLY_DEMO TO ROLE ETL_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE COSTLY_DEMO TO ROLE REPORTING_ROLE;

GRANT SELECT ON ALL TABLES IN DATABASE COSTLY_DEMO TO ROLE ANALYST_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE COSTLY_DEMO TO ROLE ETL_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE COSTLY_DEMO TO ROLE REPORTING_ROLE;

GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN DATABASE COSTLY_DEMO TO ROLE ETL_ROLE;
GRANT CREATE TABLE ON SCHEMA COSTLY_DEMO.RAW TO ROLE ETL_ROLE;
GRANT CREATE TABLE ON SCHEMA COSTLY_DEMO.SALES TO ROLE ETL_ROLE;

-- Also grant COSTLY_ROLE (your app user) read access to COSTLY_DEMO
GRANT USAGE ON DATABASE COSTLY_DEMO TO ROLE COSTLY_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE COSTLY_DEMO TO ROLE COSTLY_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE COSTLY_DEMO TO ROLE COSTLY_ROLE;

-- =============================================================
-- SECTION 4: Simulate ANALYTICS team queries (good + bad patterns)
-- =============================================================

USE ROLE ANALYST_ROLE;
USE WAREHOUSE ANALYTICS_WH;
USE DATABASE COSTLY_DEMO;

-- Good queries (efficient, uses filters)
SELECT o_orderstatus, COUNT(*) as cnt, SUM(o_totalprice) as total
FROM COSTLY_DEMO.SALES.ORDERS
WHERE o_orderdate >= '1995-01-01'
GROUP BY 1 ORDER BY 3 DESC;

SELECT c_nationkey, COUNT(DISTINCT c_custkey) as customers, AVG(c_acctbal) as avg_balance
FROM COSTLY_DEMO.SALES.CUSTOMERS
GROUP BY 1 ORDER BY 2 DESC LIMIT 25;

SELECT DATE_TRUNC('week', o_orderdate) as week, SUM(o_totalprice) as revenue
FROM COSTLY_DEMO.SALES.ORDERS
WHERE o_orderdate BETWEEN '1994-01-01' AND '1998-12-31'
GROUP BY 1 ORDER BY 1;

-- Repeated identical query (generates "repeated query" insight)
SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;
SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;
SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;
SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;
SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;

-- Bad query: SELECT * full scan (generates insight)
SELECT * FROM COSTLY_DEMO.SALES.LINEITEMS LIMIT 10000;
SELECT * FROM COSTLY_DEMO.SALES.ORDERS LIMIT 50000;

-- Expensive join (no predicate pruning)
SELECT o.o_orderkey, o.o_totalprice, l.l_quantity, l.l_extendedprice
FROM COSTLY_DEMO.SALES.ORDERS o
JOIN COSTLY_DEMO.SALES.LINEITEMS l ON o.o_orderkey = l.l_orderkey
WHERE o.o_totalprice > 100000
ORDER BY o.o_totalprice DESC
LIMIT 1000;

-- Website event aggregation (simulates dashboard query)
SELECT event_type, DATE_TRUNC('day', event_time) as day,
    COUNT(*) as events, SUM(revenue) as revenue
FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS
WHERE event_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2 ORDER BY 2 DESC, 3 DESC;

-- Repeated dashboard query pattern
SELECT event_type, COUNT(*), SUM(revenue)
FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS
GROUP BY 1;

SELECT event_type, COUNT(*), SUM(revenue)
FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS
GROUP BY 1;

SELECT event_type, COUNT(*), SUM(revenue)
FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS
GROUP BY 1;

-- =============================================================
-- SECTION 5: Simulate ETL queries (higher volume, INSERT patterns)
-- =============================================================

USE ROLE ETL_ROLE;
USE WAREHOUSE ETL_WH;

CREATE OR REPLACE TABLE COSTLY_DEMO.RAW.ORDERS_STAGING AS
SELECT *, CURRENT_TIMESTAMP() AS loaded_at
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.ORDERS;

CREATE OR REPLACE TABLE COSTLY_DEMO.RAW.LINEITEM_STAGING AS
SELECT *, CURRENT_TIMESTAMP() AS loaded_at
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.LINEITEM;

-- Simulate incremental loads (ETL pattern, runs many times)
INSERT INTO COSTLY_DEMO.RAW.ORDERS_STAGING
SELECT *, CURRENT_TIMESTAMP() AS loaded_at
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 10000;

INSERT INTO COSTLY_DEMO.RAW.ORDERS_STAGING
SELECT *, CURRENT_TIMESTAMP() AS loaded_at
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 10000;

INSERT INTO COSTLY_DEMO.RAW.ORDERS_STAGING
SELECT *, CURRENT_TIMESTAMP() AS loaded_at
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 10000;

-- Merge pattern (common ETL)
MERGE INTO COSTLY_DEMO.SALES.ORDERS t
USING (SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 5000) s
ON t.o_orderkey = s.o_orderkey
WHEN MATCHED THEN UPDATE SET t.o_totalprice = s.o_totalprice
WHEN NOT MATCHED THEN INSERT VALUES (
    s.o_orderkey, s.o_custkey, s.o_orderstatus, s.o_totalprice,
    s.o_orderdate, s.o_orderpriority, s.o_clerk, s.o_shippriority, s.o_comment
);

-- =============================================================
-- SECTION 6: Simulate REPORTING queries (BI dashboard patterns)
-- =============================================================

USE ROLE REPORTING_ROLE;
USE WAREHOUSE REPORTING_WH;

-- Same queries running over and over (Looker/Tableau pattern)
-- Revenue by month
SELECT DATE_TRUNC('month', o_orderdate) as month,
    SUM(o_totalprice) as revenue,
    COUNT(*) as orders,
    COUNT(DISTINCT o_custkey) as customers
FROM COSTLY_DEMO.SALES.ORDERS
GROUP BY 1 ORDER BY 1;

SELECT DATE_TRUNC('month', o_orderdate) as month,
    SUM(o_totalprice) as revenue,
    COUNT(*) as orders,
    COUNT(DISTINCT o_custkey) as customers
FROM COSTLY_DEMO.SALES.ORDERS
GROUP BY 1 ORDER BY 1;

SELECT DATE_TRUNC('month', o_orderdate) as month,
    SUM(o_totalprice) as revenue,
    COUNT(*) as orders,
    COUNT(DISTINCT o_custkey) as customers
FROM COSTLY_DEMO.SALES.ORDERS
GROUP BY 1 ORDER BY 1;

-- Top customers report
SELECT c.c_name, c.c_nationkey, SUM(o.o_totalprice) as total_spend
FROM COSTLY_DEMO.SALES.CUSTOMERS c
JOIN COSTLY_DEMO.SALES.ORDERS o ON c.c_custkey = o.o_custkey
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 100;

SELECT c.c_name, c.c_nationkey, SUM(o.o_totalprice) as total_spend
FROM COSTLY_DEMO.SALES.CUSTOMERS c
JOIN COSTLY_DEMO.SALES.ORDERS o ON c.c_custkey = o.o_custkey
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 100;

-- =============================================================
-- SECTION 7: Simulate DEV queries (ad-hoc, expensive, no patterns)
-- =============================================================

USE ROLE ANALYST_ROLE;
USE WAREHOUSE DEV_WH;

-- Expensive exploratory queries (no LIMIT, full scans)
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.ORDERS LIMIT 100000;
SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM LIMIT 200000;

-- Cross joins (nightmare query)
SELECT COUNT(*)
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS o
CROSS JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER c
LIMIT 1;

-- Complex multi-join analytics
SELECT
    n.n_name as nation,
    DATE_TRUNC('year', o.o_orderdate) as year,
    SUM(l.l_extendedprice * (1 - l.l_discount) - ps.ps_supplycost * l.l_quantity) as profit
FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.NATION n
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.REGION r ON n.n_regionkey = r.r_regionkey
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.SUPPLIER s ON s.s_nationkey = n.n_nationkey
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.PARTSUPP ps ON s.s_suppkey = ps.ps_suppkey
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.LINEITEM l ON l.l_suppkey = s.s_suppkey AND l.l_partkey = ps.ps_partkey
JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.ORDERS o ON o.o_orderkey = l.l_orderkey
WHERE o.o_orderdate BETWEEN '1995-01-01' AND '1996-12-31'
GROUP BY 1, 2 ORDER BY 1, 2;

-- =============================================================
-- SECTION 8: Idle warehouse (generates "idle credit waste" insight)
-- =============================================================

USE ROLE ACCOUNTADMIN;

-- Start a warehouse and don't do much — generates billing hours with low utilization
ALTER WAREHOUSE REPORTING_WH SET AUTO_SUSPEND = 300;
USE WAREHOUSE REPORTING_WH;
SELECT 1; -- tiny query to start it
SELECT CURRENT_TIMESTAMP(); -- another tiny query
-- It will keep billing for 5 minutes doing nothing

-- =============================================================
-- SECTION 9: Query tags (simulates dbt / application tagging)
-- =============================================================

USE ROLE ANALYST_ROLE;
USE WAREHOUSE ANALYTICS_WH;

ALTER SESSION SET QUERY_TAG = '{"team":"analytics","model":"fct_orders","dbt_run_id":"run_20260219_001"}';
SELECT DATE_TRUNC('month', o_orderdate), SUM(o_totalprice)
FROM COSTLY_DEMO.SALES.ORDERS GROUP BY 1;

ALTER SESSION SET QUERY_TAG = '{"team":"analytics","model":"fct_customers","dbt_run_id":"run_20260219_001"}';
SELECT c_nationkey, AVG(c_acctbal)
FROM COSTLY_DEMO.SALES.CUSTOMERS GROUP BY 1;

ALTER SESSION SET QUERY_TAG = '{"team":"etl","pipeline":"fivetran","connector":"postgres_prod"}';
USE ROLE ETL_ROLE;
USE WAREHOUSE ETL_WH;
SELECT COUNT(*) FROM COSTLY_DEMO.RAW.ORDERS_STAGING;

ALTER SESSION SET QUERY_TAG = '';

-- =============================================================
-- SECTION 10: Check data is generating
-- (Run these AFTER everything above to verify)
-- =============================================================

USE ROLE ACCOUNTADMIN;

-- Recent queries (no function args — filter with WHERE)
SELECT query_id, user_name, warehouse_name, query_type,
       total_elapsed_time/1000 AS seconds,
       LEFT(query_text, 80) AS query_preview
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE start_time > DATEADD('hour', -1, CURRENT_TIMESTAMP())
ORDER BY start_time DESC
LIMIT 50;

-- Warehouse credits (view, not function — query directly)
SELECT warehouse_name, SUM(credits_used) AS credits_today
FROM INFORMATION_SCHEMA.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 2 DESC;

-- NOTE: ACCOUNT_USAGE views have 45-min to 3-hour latency.
-- After waiting, check:
-- SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY WHERE START_TIME > DATEADD('hour', -2, CURRENT_TIMESTAMP());
-- SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY WHERE START_TIME > DATEADD('day', -1, CURRENT_TIMESTAMP());
