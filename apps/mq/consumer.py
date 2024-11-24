import asyncio
import aio_pika
import json
import logging
from datetime import datetime, timezone
from apps.db import get_session
from apps.chats.models.chats import ChatMessageInDB
from apps.mq.connection import RabbitMQConnectionManager
from apps.core.config import settings

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 100  # Максимальный размер пакета
FLUSH_INTERVAL = 30  # Интервал сброса в секундах
message_buffer = []  # Буфер для сообщений

rabbit_connection_manager = RabbitMQConnectionManager(settings.mq_settings.broker_url)

async def save_message_batch_to_db(batch_data: list, session):
    """
    Сохраняет пакет сообщений в базу данных.
    """
    try:
        session.add_all(batch_data)
        await session.commit()
        logger.debug(f"Batch of {len(batch_data)} messages saved to DB.")
    except Exception as e:
        logger.error(f"Error saving batch to DB: {e}")
        await session.rollback()
        raise e

async def flush_message_buffer():
    global message_buffer
    if not message_buffer:
        return

    try:
        async for session in get_session():
            valid_messages = [
                ChatMessageInDB(
                    action=msg["action"],
                    username=msg["username"],
                    channel=msg["channel"],
                    time=datetime.fromisoformat(msg["time"]).replace(tzinfo=timezone.utc),
                    sequence_number=msg["sequence_number"],
                    message=msg.get("message") or "No message"
                )
                for msg in message_buffer

            ]

            if valid_messages:
                await save_message_batch_to_db(valid_messages, session)
                message_buffer.clear()

    except Exception as e:
        logger.error(f"Error flushing message buffer: {e}")

async def on_message(message):

    global message_buffer
    async with message.process():
        try:
            message_data = json.loads(message.body.decode("utf-8"))
            logger.debug(f"Received message: {message_data}")

            message_buffer.append(message_data)

            if len(message_buffer) >= MAX_BATCH_SIZE:
                await flush_message_buffer()

            await message.ack()
        except Exception as e:
            logger.error(f"Error processing message from RabbitMQ: {e}")
            await message.nack(requeue=True)


async def start_consumer(queue_name: str):
    try:
        connection = await aio_pika.connect_robust(settings.mq_settings.broker_url)
        async with connection:
            channel = await connection.channel()

            queue = await channel.declare_queue(queue_name, durable=True)

            logger.info(f"Queue '{queue_name}' is ready. Waiting for messages...")

            await queue.consume(on_message, no_ack=False)
            while True:
                await asyncio.sleep(FLUSH_INTERVAL)
                await flush_message_buffer()

    except aio_pika.exceptions.AMQPChannelError as e:
        logger.error(f"Channel error when setting up consumer for queue '{queue_name}': {e}")
    except Exception as e:
        logger.error(f"Error during consumer setup for queue '{queue_name}': {e}")
        raise e