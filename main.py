from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.router import api_router
from app.core.config import settings
from app.core.db import create_db_and_tables, wait_for_db
from app.utils.metrics import PrometheusMiddleware

app = FastAPI(
    title="Task Manager API",
    description="API for managing tasks with extended features",
    version="0.1.0",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# Set up metrics endpoint for Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API router
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    wait_for_db()
    create_db_and_tables()


@app.get("/")
async def root():
    return {"message": "Task Manager API is running"}


if __name__ == "__main__":
    import uvicorn
    from app.utils.uvicorn_config import UVICORN_CONFIG

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        **UVICORN_CONFIG
    )
