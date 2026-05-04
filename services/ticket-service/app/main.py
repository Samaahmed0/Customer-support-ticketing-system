import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from prometheus_client import Counter, generate_latest
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.config import settings
from app.database import get_db, init_db
from app.messaging import messaging
from app.models import Ticket
from ticketing_shared.events import EventRoutingKey
from ticketing_shared.schemas import HealthResponse, TicketCreate, TicketResponse, TicketStatus, TicketUpdate

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

tickets_created = Counter("ticketing_tickets_created_total", "Tickets created", ["service"])
tickets_updated = Counter("ticketing_tickets_updated_total", "Tickets updated", ["service"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await messaging.connect()
    yield
    await messaging.close()


app = FastAPI(title="Ticket Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=settings.service_name)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/tickets", response_model=TicketResponse)
async def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    ticket = Ticket(title=payload.title, description=payload.description or "", status=TicketStatus.OPEN.value)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    tickets_created.labels(service=settings.service_name).inc()
    await messaging.publish(
        EventRoutingKey.TICKET_CREATED,
        {"ticket_id": ticket.id, "title": ticket.title, "status": ticket.status},
    )
    return ticket


@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets(db: Session = Depends(get_db)):
    return db.query(Ticket).order_by(Ticket.id.desc()).all()


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if payload.title is not None:
        ticket.title = payload.title
    if payload.description is not None:
        ticket.description = payload.description
    if payload.status is not None:
        ticket.status = payload.status.value
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    tickets_updated.labels(service=settings.service_name).inc()
    await messaging.publish(
        EventRoutingKey.TICKET_UPDATED,
        {"ticket_id": ticket.id, "status": ticket.status, "title": ticket.title},
    )
    return ticket
