import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, increment_counter
from ticketing_shared.events import EventRoutingKey

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "ticketing.events"
QUEUE_NAME = "reporting.events"


async def run_consumer() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
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
                    try:
                        payload = json.loads(message.body.decode("utf-8"))
                        rk = message.routing_key or ""
                        with SessionLocal() as db:
                            if rk == EventRoutingKey.TICKET_CREATED.value:
                                increment_counter(db, "tickets_created")
                            elif rk == EventRoutingKey.TICKET_UPDATED.value:
                                increment_counter(db, "tickets_updated")
                            elif rk == EventRoutingKey.SUPPORT_MESSAGE.value:
                                increment_counter(db, "support_messages")
                            elif rk == EventRoutingKey.SUPPORT_RESOLVED.value:
                                increment_counter(db, "support_resolved")
                        logger.debug("Processed reporting event %s %s", rk, payload)
                    except Exception:
                        logger.exception("Failed to process reporting message")
    except asyncio.CancelledError:
        logger.info("Reporting consumer cancelled")
        raise
    finally:
        await connection.close()
