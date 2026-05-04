from enum import Enum


class EventRoutingKey(str, Enum):
    """Topic routing keys published to exchange ``ticketing.events``."""

    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    SUPPORT_MESSAGE = "support.message"
    SUPPORT_RESOLVED = "support.resolved"
