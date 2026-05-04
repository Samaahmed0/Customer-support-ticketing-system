import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from prometheus_client import Gauge, generate_latest
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.config import settings
from app.consumer import run_consumer
from app.database import SessionLocal, get_summary, init_db
from app.models import ReportingCounter
from ticketing_shared.schemas import HealthResponse

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(run_consumer())
    app.state.reporting_task = task
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Reporting Service", version="0.1.0", lifespan=lifespan)

reporting_tickets_created = Gauge("ticketing_report_tickets_created", "DB aggregate", ["service"])
reporting_tickets_updated = Gauge("ticketing_report_tickets_updated", "DB aggregate", ["service"])
reporting_support_messages = Gauge("ticketing_report_support_messages", "DB aggregate", ["service"])
reporting_support_resolved = Gauge("ticketing_report_support_resolved", "DB aggregate", ["service"])


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=settings.service_name)


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    try:
        row = get_summary(db)
        reporting_tickets_created.labels(service=settings.service_name).set(row.tickets_created)
        reporting_tickets_updated.labels(service=settings.service_name).set(row.tickets_updated)
        reporting_support_messages.labels(service=settings.service_name).set(row.support_messages)
        reporting_support_resolved.labels(service=settings.service_name).set(row.support_resolved)
    except Exception:
        logger.exception("Could not refresh gauges from DB")
    return Response(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/reports/summary")
def summary(db: Session = Depends(get_db)):
    row: ReportingCounter = get_summary(db)
    return {
        "tickets_created": row.tickets_created,
        "tickets_updated": row.tickets_updated,
        "support_messages": row.support_messages,
        "support_resolved": row.support_resolved,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
