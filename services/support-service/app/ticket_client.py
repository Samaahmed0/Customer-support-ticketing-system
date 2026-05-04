import httpx
from fastapi import HTTPException

from app.config import settings
from ticketing_shared.schemas import TicketResponse, TicketStatus, TicketUpdate


async def fetch_ticket(ticket_id: int) -> TicketResponse:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{settings.ticket_service_url.rstrip('/')}/tickets/{ticket_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ticket service error: {r.status_code}")
    return TicketResponse.model_validate(r.json())


async def patch_ticket_status(ticket_id: int, status: TicketStatus) -> TicketResponse:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.patch(
            f"{settings.ticket_service_url.rstrip('/')}/tickets/{ticket_id}",
            json=TicketUpdate(status=status).model_dump(exclude_none=True),
        )
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ticket service error: {r.status_code}")
    return TicketResponse.model_validate(r.json())
