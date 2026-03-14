# dbt Cloud Billing & Cost Expert Knowledge Base

## Pricing Model

dbt Cloud bills based on **plan tier + successful model builds**.

### Plans
| Plan | Price | Includes |
|------|-------|----------|
| Developer | Free | 1 project, 1 user, manual runs only |
| Team | $100/seat/month | Unlimited projects, CI, scheduling |
| Enterprise | Custom | SSO, RBAC, audit logs, SLA |

### Model Build Pricing (Team+ plans)
- Models built = successful model executions
- Included models vary by plan
- Overage: ~$0.01-0.03 per model build (varies)

## The Real Cost: Warehouse Compute

dbt Cloud's own bill is usually small. The **warehouse compute it triggers** is the real cost:
- Each `dbt run` spins up warehouse compute (Snowflake credits, BigQuery slots, etc.)
- A full-refresh of 200 models on a Large Snowflake warehouse = 200 × model_runtime × 8 credits/hr
- **The dbt bill is the tip of the iceberg — the warehouse bill is the iceberg**

## Cost Optimization Strategies

1. **Incremental models** — 5-20x cheaper than full-refresh for large tables
   - `materialized='incremental'` with `unique_key` and proper `is_incremental()` logic
   - Full-refresh only when schema changes or data quality requires it

2. **Model selection in CI** — Don't run all models on every PR
   - `dbt build --select state:modified+` — only changed models + downstream
   - Slim CI saves 80%+ on CI warehouse costs

3. **Warehouse per job type** — Don't use one big warehouse for everything
   - Hourly incremental: Small warehouse
   - Daily full-refresh: Medium warehouse
   - Monthly rebuild: Large warehouse (short burst)

4. **Defer to production** — CI jobs reference prod models instead of rebuilding everything

5. **Reduce model count** — Excessive intermediate models increase build time
   - Ephemeral models compile to CTEs (no warehouse cost)
   - Consolidate staging models where possible

## Common Cost Problems

### 1. "dbt jobs are our biggest Snowflake cost"
- Full-refresh on tables that should be incremental
- Running all 500 models on every schedule instead of only changed
- Fix: Incremental materialization + model selection

### 2. "CI is burning credits"
- Every PR runs the full project
- Fix: `dbt build --select state:modified+` with `--defer`

### 3. "Development is expensive"
- Developers running `dbt run` on Large warehouses
- Fix: Dev profiles use X-Small warehouse, limit to subset of models
