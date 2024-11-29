import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika

from apps.chats.models.chats import ChatMessageInDB
from apps.core.config import settings
from apps.db import get_session
from apps.mq.connection import RabbitMQConnectionManager

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
        logger.error(f"Ошибка очистки буфера сообщений: {e}")
        raise

async def on_message(message):
    """Прием сообщения из очереди"""
    global message_buffer
    async with message.process():
        try:
  
            message_data = json.loads(message.body.decode("utf-8"))
            logger.debug(f"Получено сообщение: {message_data}")

            message_buffer.append(message_data)

            if len(message_buffer) >= MAX_BATCH_SIZE:
                await flush_message_buffer()

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при декодировании сообщения: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка обработки сообщения: {e}")
            raise

async def start_consumer(queue_name: str):
    """Запуск consumer"""
    try:
        connection = await aio_pika.connect_robust(settings.mq_settings.broker_url)
        async with connection:
            channel = await connection.channel()

            queue = await channel.declare_queue(queue_name, durable=True)

            logger.info(f"Очередь '{queue_name}' готова. Ожидаются сообщения...")

            await queue.consume(on_message, no_ack=False)
            while True:
                await asyncio.sleep(FLUSH_INTERVAL)
                await flush_message_buffer()

    except aio_pika.exceptions.AMQPChannelError as e:
        logger.error(f"Ошибка канала при настройке потребителя для очереди '{queue_name}': {e}")
    except Exception as e:
        logger.error(f"Ошибка при настройке очереди потребителя '{queue_name}': {e}")
        raise e