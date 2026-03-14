-- =============================================================
-- Costly — Multi-Day Usage Simulator
-- Creates Snowflake Tasks that run automatically over days,
-- generating realistic ACCOUNT_USAGE data across warehouses,
-- roles, and query patterns.
--
-- PREREQS:
--   Run generate_snowflake_demo_data.sql first to create
--   warehouses, roles, databases, and tables.
--
-- HOW TO USE:
--   1. Paste into a Snowflake worksheet as ACCOUNTADMIN
--   2. Run the whole script
--   3. Tasks start automatically — let them run for 3-7 days
--   4. Run the CLEANUP section at the bottom when done
--
-- CREDIT USAGE:
--   ~2-4 credits/day (mostly XSMALL/SMALL warehouses)
--   Safe for a trial account's 400 free credits over a week
-- =============================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE COSTLY_DEMO;

-- =============================================================
-- SECTION 1: Stored procedures (the query workloads)
-- =============================================================

-- Analytics team: dashboard queries, repeated aggregations, some full scans
CREATE OR REPLACE PROCEDURE COSTLY_DEMO.PUBLIC.SP_ANALYTICS_WORKLOAD()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    USE WAREHOUSE ANALYTICS_WH;

    -- Dashboard KPI query (runs every time, highly cacheable)
    SELECT o_orderstatus, COUNT(*) AS cnt, SUM(o_totalprice) AS total
    FROM COSTLY_DEMO.SALES.ORDERS
    WHERE o_orderdate >= '1995-01-01'
    GROUP BY 1 ORDER BY 3 DESC;

    -- Weekly revenue trend
    SELECT DATE_TRUNC('week', o_orderdate) AS week, SUM(o_totalprice) AS revenue
    FROM COSTLY_DEMO.SALES.ORDERS
    WHERE o_orderdate BETWEEN '1994-01-01' AND '1998-12-31'
    GROUP BY 1 ORDER BY 1;

    -- Customer segmentation
    SELECT c_nationkey, COUNT(DISTINCT c_custkey) AS customers, AVG(c_acctbal) AS avg_balance
    FROM COSTLY_DEMO.SALES.CUSTOMERS
    GROUP BY 1 ORDER BY 2 DESC LIMIT 25;

    -- Marketing events dashboard
    SELECT event_type, DATE_TRUNC('day', event_time) AS day,
        COUNT(*) AS events, SUM(revenue) AS revenue
    FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS
    WHERE event_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
    GROUP BY 1, 2 ORDER BY 2 DESC, 3 DESC;

    -- Repeated identical query (generates "cacheable" pattern)
    SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;
    SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;
    SELECT COUNT(*) FROM COSTLY_DEMO.SALES.ORDERS;

    -- Bad query: full table scan (generates "full_scan" flag)
    SELECT * FROM COSTLY_DEMO.SALES.LINEITEMS LIMIT 10000;

    RETURN 'analytics_workload_complete';
END;
$$;


-- ETL team: heavy writes, staging loads, merges
CREATE OR REPLACE PROCEDURE COSTLY_DEMO.PUBLIC.SP_ETL_WORKLOAD()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    USE WAREHOUSE ETL_WH;

    -- Incremental load simulation
    INSERT INTO COSTLY_DEMO.RAW.ORDERS_STAGING
    SELECT *, CURRENT_TIMESTAMP() AS loaded_at
    FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS
    LIMIT 10000;

    -- Another incremental load
    INSERT INTO COSTLY_DEMO.RAW.ORDERS_STAGING
    SELECT *, CURRENT_TIMESTAMP() AS loaded_at
    FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS
    LIMIT 5000;

    -- Merge pattern (common dbt incremental)
    MERGE INTO COSTLY_DEMO.SALES.ORDERS t
    USING (SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 5000) s
    ON t.o_orderkey = s.o_orderkey
    WHEN MATCHED THEN UPDATE SET t.o_totalprice = s.o_totalprice
    WHEN NOT MATCHED THEN INSERT VALUES (
        s.o_orderkey, s.o_custkey, s.o_orderstatus, s.o_totalprice,
        s.o_orderdate, s.o_orderpriority, s.o_clerk, s.o_shippriority, s.o_comment
    );

    -- Heavy aggregation (simulates dbt model build)
    CREATE OR REPLACE TABLE COSTLY_DEMO.SALES.FCT_DAILY_REVENUE AS
    SELECT
        o_orderdate AS order_date,
        COUNT(*) AS order_count,
        SUM(o_totalprice) AS total_revenue,
        AVG(o_totalprice) AS avg_order_value,
        COUNT(DISTINCT o_custkey) AS unique_customers
    FROM COSTLY_DEMO.SALES.ORDERS
    GROUP BY 1;

    -- Staging row count check (pipeline validation)
    SELECT COUNT(*) FROM COSTLY_DEMO.RAW.ORDERS_STAGING;

    RETURN 'etl_workload_complete';
END;
$$;


-- Reporting team: BI dashboard refreshes, same queries over and over
CREATE OR REPLACE PROCEDURE COSTLY_DEMO.PUBLIC.SP_REPORTING_WORKLOAD()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    USE WAREHOUSE REPORTING_WH;

    -- Revenue by month (Looker/Tableau dashboard tile)
    SELECT DATE_TRUNC('month', o_orderdate) AS month,
        SUM(o_totalprice) AS revenue,
        COUNT(*) AS orders,
        COUNT(DISTINCT o_custkey) AS customers
    FROM COSTLY_DEMO.SALES.ORDERS
    GROUP BY 1 ORDER BY 1;

    -- Same query again (simulates dashboard auto-refresh)
    SELECT DATE_TRUNC('month', o_orderdate) AS month,
        SUM(o_totalprice) AS revenue,
        COUNT(*) AS orders,
        COUNT(DISTINCT o_custkey) AS customers
    FROM COSTLY_DEMO.SALES.ORDERS
    GROUP BY 1 ORDER BY 1;

    -- Top customers report
    SELECT c.c_name, c.c_nationkey, SUM(o.o_totalprice) AS total_spend
    FROM COSTLY_DEMO.SALES.CUSTOMERS c
    JOIN COSTLY_DEMO.SALES.ORDERS o ON c.c_custkey = o.o_custkey
    GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 100;

    -- Same top customers (duplicate refresh)
    SELECT c.c_name, c.c_nationkey, SUM(o.o_totalprice) AS total_spend
    FROM COSTLY_DEMO.SALES.CUSTOMERS c
    JOIN COSTLY_DEMO.SALES.ORDERS o ON c.c_custkey = o.o_custkey
    GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 100;

    -- Event summary for marketing dashboard
    SELECT event_type, COUNT(*), SUM(revenue)
    FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS
    GROUP BY 1;

    RETURN 'reporting_workload_complete';
END;
$$;


-- Dev team: ad-hoc expensive queries, cross joins, exploratory scans
CREATE OR REPLACE PROCEDURE COSTLY_DEMO.PUBLIC.SP_DEV_WORKLOAD()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    USE WAREHOUSE DEV_WH;

    -- Expensive full scan on large dataset
    SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.ORDERS LIMIT 100000;

    -- Large lineitem scan
    SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM LIMIT 200000;

    -- Cross join (wasteful)
    SELECT COUNT(*)
    FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS o
    CROSS JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER c
    LIMIT 1;

    -- Complex multi-join analytics
    SELECT
        n.n_name AS nation,
        DATE_TRUNC('year', o.o_orderdate) AS year,
        SUM(l.l_extendedprice * (1 - l.l_discount) - ps.ps_supplycost * l.l_quantity) AS profit
    FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.NATION n
    JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.REGION r ON n.n_regionkey = r.r_regionkey
    JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.SUPPLIER s ON s.s_nationkey = n.n_nationkey
    JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.PARTSUPP ps ON s.s_suppkey = ps.ps_suppkey
    JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.LINEITEM l ON l.l_suppkey = s.s_suppkey AND l.l_partkey = ps.ps_partkey
    JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF10.ORDERS o ON o.o_orderkey = l.l_orderkey
    WHERE o.o_orderdate BETWEEN '1995-01-01' AND '1996-12-31'
    GROUP BY 1, 2 ORDER BY 1, 2;

    RETURN 'dev_workload_complete';
END;
$$;


-- Idle warehouse simulator: starts warehouse, runs tiny query, wastes credits
CREATE OR REPLACE PROCEDURE COSTLY_DEMO.PUBLIC.SP_IDLE_WASTE()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    ALTER WAREHOUSE REPORTING_WH SET AUTO_SUSPEND = 300;
    USE WAREHOUSE REPORTING_WH;
    SELECT 1;
    SELECT CURRENT_TIMESTAMP();
    -- Warehouse stays running for 5 min doing nothing
    RETURN 'idle_waste_complete';
END;
$$;


-- dbt-tagged queries: simulates tagged pipeline runs
CREATE OR REPLACE PROCEDURE COSTLY_DEMO.PUBLIC.SP_TAGGED_QUERIES()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    USE WAREHOUSE ANALYTICS_WH;

    ALTER SESSION SET QUERY_TAG = '{"team":"analytics","model":"fct_orders","dbt_run_id":"run_daily"}';
    SELECT DATE_TRUNC('month', o_orderdate), SUM(o_totalprice)
    FROM COSTLY_DEMO.SALES.ORDERS GROUP BY 1;

    ALTER SESSION SET QUERY_TAG = '{"team":"analytics","model":"fct_customers","dbt_run_id":"run_daily"}';
    SELECT c_nationkey, AVG(c_acctbal)
    FROM COSTLY_DEMO.SALES.CUSTOMERS GROUP BY 1;

    ALTER SESSION SET QUERY_TAG = '{"team":"analytics","model":"dim_events","dbt_run_id":"run_daily"}';
    SELECT event_type, COUNT(*) FROM COSTLY_DEMO.MARKETING.WEBSITE_EVENTS GROUP BY 1;

    USE WAREHOUSE ETL_WH;
    ALTER SESSION SET QUERY_TAG = '{"team":"etl","pipeline":"fivetran","connector":"postgres_prod"}';
    SELECT COUNT(*) FROM COSTLY_DEMO.RAW.ORDERS_STAGING;

    ALTER SESSION SET QUERY_TAG = '';

    RETURN 'tagged_queries_complete';
END;
$$;


-- =============================================================
-- SECTION 2: Grant execute on procedures to roles
-- =============================================================

GRANT USAGE ON SCHEMA COSTLY_DEMO.PUBLIC TO ROLE ANALYST_ROLE;
GRANT USAGE ON SCHEMA COSTLY_DEMO.PUBLIC TO ROLE ETL_ROLE;
GRANT USAGE ON SCHEMA COSTLY_DEMO.PUBLIC TO ROLE REPORTING_ROLE;


-- =============================================================
-- SECTION 3: Create scheduled tasks
-- =============================================================

-- Analytics: every 2 hours (simulates active dashboard users)
CREATE OR REPLACE TASK COSTLY_DEMO.PUBLIC.TASK_ANALYTICS
    WAREHOUSE = 'ANALYTICS_WH'
    SCHEDULE  = 'USING CRON 0 */2 * * * America/New_York'
    COMMENT   = 'Costly simulator: analytics team queries'
AS
    CALL COSTLY_DEMO.PUBLIC.SP_ANALYTICS_WORKLOAD();

-- ETL: every 6 hours (simulates pipeline schedule)
CREATE OR REPLACE TASK COSTLY_DEMO.PUBLIC.TASK_ETL
    WAREHOUSE = 'ETL_WH'
    SCHEDULE  = 'USING CRON 0 */6 * * * America/New_York'
    COMMENT   = 'Costly simulator: ETL pipeline runs'
AS
    CALL COSTLY_DEMO.PUBLIC.SP_ETL_WORKLOAD();

-- Reporting: every 4 hours during business hours (simulates BI refreshes)
CREATE OR REPLACE TASK COSTLY_DEMO.PUBLIC.TASK_REPORTING
    WAREHOUSE = 'REPORTING_WH'
    SCHEDULE  = 'USING CRON 0 6,10,14,18,22 * * * America/New_York'
    COMMENT   = 'Costly simulator: BI dashboard refreshes'
AS
    CALL COSTLY_DEMO.PUBLIC.SP_REPORTING_WORKLOAD();

-- Dev: once daily at 3pm (simulates ad-hoc exploration)
CREATE OR REPLACE TASK COSTLY_DEMO.PUBLIC.TASK_DEV
    WAREHOUSE = 'DEV_WH'
    SCHEDULE  = 'USING CRON 0 15 * * * America/New_York'
    COMMENT   = 'Costly simulator: dev ad-hoc queries'
AS
    CALL COSTLY_DEMO.PUBLIC.SP_DEV_WORKLOAD();

-- Idle waste: twice daily (simulates idle warehouse burn)
CREATE OR REPLACE TASK COSTLY_DEMO.PUBLIC.TASK_IDLE_WASTE
    WAREHOUSE = 'REPORTING_WH'
    SCHEDULE  = 'USING CRON 0 9,21 * * * America/New_York'
    COMMENT   = 'Costly simulator: idle warehouse waste'
AS
    CALL COSTLY_DEMO.PUBLIC.SP_IDLE_WASTE();

-- dbt tags: every 8 hours (simulates dbt Cloud scheduled runs)
CREATE OR REPLACE TASK COSTLY_DEMO.PUBLIC.TASK_TAGGED
    WAREHOUSE = 'ANALYTICS_WH'
    SCHEDULE  = 'USING CRON 0 2,10,18 * * * America/New_York'
    COMMENT   = 'Costly simulator: dbt-tagged pipeline runs'
AS
    CALL COSTLY_DEMO.PUBLIC.SP_TAGGED_QUERIES();


-- =============================================================
-- SECTION 4: Resume all tasks (tasks are created SUSPENDED)
-- =============================================================

ALTER TASK COSTLY_DEMO.PUBLIC.TASK_ANALYTICS RESUME;
ALTER TASK COSTLY_DEMO.PUBLIC.TASK_ETL RESUME;
ALTER TASK COSTLY_DEMO.PUBLIC.TASK_REPORTING RESUME;
ALTER TASK COSTLY_DEMO.PUBLIC.TASK_DEV RESUME;
ALTER TASK COSTLY_DEMO.PUBLIC.TASK_IDLE_WASTE RESUME;
ALTER TASK COSTLY_DEMO.PUBLIC.TASK_TAGGED RESUME;


-- =============================================================
-- SECTION 5: Verify tasks are running
-- =============================================================

SHOW TASKS IN COSTLY_DEMO.PUBLIC;

-- Check task run history (wait a few hours then run this):
-- SELECT *
-- FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
-- WHERE DATABASE_NAME = 'COSTLY_DEMO'
-- ORDER BY SCHEDULED_TIME DESC
-- LIMIT 20;


-- =============================================================
-- CLEANUP: Run this when you're done simulating (after 3-7 days)
-- =============================================================
-- ALTER TASK COSTLY_DEMO.PUBLIC.TASK_ANALYTICS SUSPEND;
-- ALTER TASK COSTLY_DEMO.PUBLIC.TASK_ETL SUSPEND;
-- ALTER TASK COSTLY_DEMO.PUBLIC.TASK_REPORTING SUSPEND;
-- ALTER TASK COSTLY_DEMO.PUBLIC.TASK_DEV SUSPEND;
-- ALTER TASK COSTLY_DEMO.PUBLIC.TASK_IDLE_WASTE SUSPEND;
-- ALTER TASK COSTLY_DEMO.PUBLIC.TASK_TAGGED SUSPEND;
--
-- DROP TASK IF EXISTS COSTLY_DEMO.PUBLIC.TASK_ANALYTICS;
-- DROP TASK IF EXISTS COSTLY_DEMO.PUBLIC.TASK_ETL;
-- DROP TASK IF EXISTS COSTLY_DEMO.PUBLIC.TASK_REPORTING;
-- DROP TASK IF EXISTS COSTLY_DEMO.PUBLIC.TASK_DEV;
-- DROP TASK IF EXISTS COSTLY_DEMO.PUBLIC.TASK_IDLE_WASTE;
-- DROP TASK IF EXISTS COSTLY_DEMO.PUBLIC.TASK_TAGGED;
