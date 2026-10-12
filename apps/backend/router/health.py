import os
from time import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from service.health import Health
from util.helper import get_execution_time, router_param_builder

obj = Health()

tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag, jwt=False))


@router.get("")
def liveness():
    """Process is up. No dependency checks — used by Docker/orchestrator liveness probes."""
    return {"status": "ok"}


@router.get("/ready")
def readiness():
    """Checks every configured backing service. Returns 503 if any of them is down."""
    start_time = time()
    checks = obj.check_all()
    healthy = all(check["status"] in ("ok", "not_configured") for check in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "checks": checks,
            "executionTime": get_execution_time(start_time),
        },
    )
