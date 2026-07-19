"""
Health check endpoints for the API, models, and database.
"""

import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.services.model_manager import model_manager

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
@router.get("/")
def health_root():
    """Basic health check (liveness)."""
    return {"status": "ok", "service": "Healthcare Risk Prediction API"}


@router.get("/models")
def health_models():
    """Model health endpoint returning inference readiness, latency, and
    versions."""
    status_data = model_manager.get_health_status()
    # Determine overall status: ready if at least one model is ready
    models_ready = any(
        m["status"] == "ready" for m in status_data["models"].values()
    )

    response = {
        "status": "ready" if models_ready else "degraded",
        "models": status_data["models"],
        "diagnostics": status_data["diagnostics"],
    }

    if not models_ready:
        return JSONResponse(status_code=503, content=response)
    return response


@router.get("/database")
async def health_database():
    """Database health check."""
    try:
        with sqlite3.connect(":memory:") as db:
            result = db.execute("SELECT 1").fetchone()
        if result and result[0] == 1:
            return {"status": "healthy", "latency_ms": 0.0}
    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )
    return {
        "status": "unknown",
        "message": "Database check not fully configured",
    }
