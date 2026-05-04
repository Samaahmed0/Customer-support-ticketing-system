import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.config import settings
from ticketing_shared.events import EventRoutingKey

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "ticketing.events"


class Messaging:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        logger.info("support-service connected to RabbitMQ")

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None

    async def publish(self, routing_key: EventRoutingKey, payload: dict[str, Any]) -> None:
        if not self._exchange:
            raise RuntimeError("Messaging not connected")
        body = json.dumps(payload, default=str).encode("utf-8")
        await self._exchange.publish(
            aio_pika.Message(body=body, content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=routing_key.value,
        )


messaging = Messaging()
