from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str


class SupportMessageCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=10000)


class SupportMessageResponse(BaseModel):
    id: int
    ticket_id: int
    agent_id: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignTicketRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=200)


class SupportAssignmentResponse(BaseModel):
    id: int
    ticket_id: int
    agent_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
