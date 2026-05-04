import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType
from prometheus_client import Counter

from app.config import settings
from ticketing_shared.events import EventRoutingKey

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "ticketing.events"
QUEUE_NAME = "notification.events"

notifications_delivered = Counter(
    "ticketing_notifications_processed_total", "Notification events handled", ["service", "routing_key"]
)


async def run_consumer() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=20)
        exchange = await channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        for key in (
            EventRoutingKey.TICKET_CREATED.value,
            EventRoutingKey.TICKET_UPDATED.value,
            EventRoutingKey.SUPPORT_MESSAGE.value,
            EventRoutingKey.SUPPORT_RESOLVED.value,
        ):
            await queue.bind(exchange, routing_key=key)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    rk = message.routing_key or ""
                    payload = json.loads(message.body.decode("utf-8"))
                    # In production: send email/push/webhook. Here: structured log for Loki/Promtail.
                    logger.info(
                        "NOTIFY routing_key=%s payload=%s",
                        rk,
                        payload,
                        extra={"routing_key": rk, "payload": payload},
                    )
                    notifications_delivered.labels(service=settings.service_name, routing_key=rk).inc()
    except asyncio.CancelledError:
        logger.info("Notification consumer cancelled")
        raise
    finally:
        await connection.close()
