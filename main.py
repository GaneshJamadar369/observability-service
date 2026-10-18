
import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

EMAIL = "23f3003450@ds.study.iitm.ac.in"
START_TIME = time.monotonic()

REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
)

LOGS = deque(maxlen=1000)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            REQUESTS.inc()
            LOGS.append({
                "level": "INFO" if status_code < 500 else "ERROR",
                "ts": datetime.now(timezone.utc).isoformat(),
                "path": request.url.path,
                "request_id": request_id,
                "method": request.method,
                "status_code": status_code,
                "duration_s": round(time.perf_counter() - start, 6),
            })


app.add_middleware(ObservabilityMiddleware)


@app.get("/work")
def work(n: int = Query(..., ge=0, le=100000)):
    # Perform K units of work.
    done = 0
    for i in range(n):
        done += 1
    return {"email": EMAIL, "done": done}


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": float(time.monotonic() - START_TIME),
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/logs/tail")
def logs_tail(limit: int = Query(100, ge=1, le=1000)):
    return list(LOGS)[-limit:]
