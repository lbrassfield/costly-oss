from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import create_indexes
from app.services.alerts_engine import evaluate_all_alerts
from app.services.query_sync import sync_all_users_query_history
from app.services.cost_sync import sync_all_platform_costs

from app.routers import (
    auth, connections, dashboard, costs, queries,
    storage, warehouses, workloads, recommendations,
    alerts, history, debug, optimization, admin,
    public_demo, chat, platforms, anomalies,
)

app = FastAPI(title="costly API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(connections.router)
app.include_router(dashboard.router)
app.include_router(costs.router)
app.include_router(queries.router)
app.include_router(storage.router)
app.include_router(warehouses.router)
app.include_router(workloads.router)
app.include_router(recommendations.router)
app.include_router(alerts.router)
app.include_router(history.router)
app.include_router(debug.router)
app.include_router(optimization.router)
app.include_router(admin.router)
app.include_router(public_demo.router)
app.include_router(chat.router)
app.include_router(platforms.router)
app.include_router(anomalies.router)

_scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def startup_event():
    await create_indexes()
    _scheduler.add_job(evaluate_all_alerts, "interval", minutes=15, id="alert_evaluator")
    _scheduler.add_job(sync_all_users_query_history, "interval", hours=6, id="query_history_sync")
    _scheduler.add_job(sync_all_platform_costs, "interval", hours=6, id="platform_cost_sync")
    _scheduler.add_job(
        sync_all_users_query_history, "date",
        run_date=datetime.utcnow() + timedelta(seconds=90),
        id="query_history_boot",
    )
    _scheduler.add_job(
        sync_all_platform_costs, "date",
        run_date=datetime.utcnow() + timedelta(seconds=120),
        id="platform_cost_boot",
    )
    _scheduler.start()
    print("[STARTUP] Indexes created. Alert engine + query/cost sync scheduled.")


@app.on_event("shutdown")
async def shutdown_event():
    _scheduler.shutdown(wait=False)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
