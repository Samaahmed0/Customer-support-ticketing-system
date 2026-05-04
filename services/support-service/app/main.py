import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from prometheus_client import Counter, generate_latest
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.config import settings
from app.database import get_db, init_db
from app.messaging import messaging
from app.models import SupportAssignment, SupportMessage
from app.ticket_client import fetch_ticket, patch_ticket_status
from ticketing_shared.events import EventRoutingKey
from ticketing_shared.schemas import (
    AssignTicketRequest,
    HealthResponse,
    SupportAssignmentResponse,
    SupportMessageCreate,
    SupportMessageResponse,
    TicketStatus,
)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

support_messages = Counter("ticketing_support_messages_total", "Support messages posted", ["service"])
support_resolutions = Counter("ticketing_support_resolutions_total", "Tickets resolved via support", ["service"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await messaging.connect()
    yield
    await messaging.close()


app = FastAPI(title="Support Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=settings.service_name)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/tickets/{ticket_id}/assignments", response_model=list[SupportAssignmentResponse])
def list_assignments(ticket_id: int, db: Session = Depends(get_db)):
    return (
        db.query(SupportAssignment)
        .filter(SupportAssignment.ticket_id == ticket_id)
        .order_by(SupportAssignment.id)
        .all()
    )


@app.post("/tickets/{ticket_id}/assign")
async def assign_ticket(ticket_id: int, body: AssignTicketRequest, db: Session = Depends(get_db)):
    await fetch_ticket(ticket_id)
    row = SupportAssignment(ticket_id=ticket_id, agent_id=body.agent_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ticket_id": ticket_id, "agent_id": body.agent_id, "assignment_id": row.id}


@app.post("/tickets/{ticket_id}/messages", response_model=SupportMessageResponse)
async def post_message(ticket_id: int, body: SupportMessageCreate, db: Session = Depends(get_db)):
    await fetch_ticket(ticket_id)
    msg = SupportMessage(ticket_id=ticket_id, agent_id=body.agent_id, body=body.body)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    support_messages.labels(service=settings.service_name).inc()
    await messaging.publish(
        EventRoutingKey.SUPPORT_MESSAGE,
        {"ticket_id": ticket_id, "message_id": msg.id, "agent_id": body.agent_id},
    )
    return msg


@app.get("/tickets/{ticket_id}/messages", response_model=list[SupportMessageResponse])
def list_messages(ticket_id: int, db: Session = Depends(get_db)):
    return db.query(SupportMessage).filter(SupportMessage.ticket_id == ticket_id).order_by(SupportMessage.id).all()


@app.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int, db: Session = Depends(get_db)):
    await fetch_ticket(ticket_id)
    updated = await patch_ticket_status(ticket_id, TicketStatus.RESOLVED)
    support_resolutions.labels(service=settings.service_name).inc()
    await messaging.publish(
        EventRoutingKey.SUPPORT_RESOLVED,
        {"ticket_id": ticket_id, "status": updated.status.value},
    )
    return {"ticket_id": ticket_id, "status": updated.status.value}
