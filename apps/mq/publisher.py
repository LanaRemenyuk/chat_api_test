import json
import logging
from collections import defaultdict

import aio_pika
from aio_pika import Message

from apps.core.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

message_sequence = defaultdict(int)

async def publish_message_to_queue(queue_name: str, message_data: dict):
    """Функция для публикации сообщения в очередь"""
    try:
        logger.info(f"Попытка публикации сообщения в очередь {queue_name}: {message_data}")
        sequence_number = message_sequence[queue_name]
        message_sequence[queue_name] += 1

        message_data['sequence_number'] = sequence_number
        message_body = json.dumps(message_data, ensure_ascii=False).encode('utf-8')
        
        logger.debug(f"Сериализованное сообщение: {message_body}")

        connection = await aio_pika.connect_robust(settings.mq_settings.broker_url)
        async with connection:
            channel = await connection.channel()

            exchange = await channel.declare_exchange('default', aio_pika.ExchangeType.DIRECT, durable=True)

            queue = await channel.declare_queue(queue_name, durable=True)

            await queue.bind(exchange, routing_key=queue_name)
            logger.debug(f"Очередь {queue_name} связана с обменником 'default' с routing_key: {queue_name}")

            message = Message(
                body=message_body,
                delivery_mode=2, 
                content_type="application/json"
            )

            await exchange.publish(message, routing_key=queue_name)
            logger.info(f"Сообщение успешно опубликовано в очередь {queue_name}: {message_data}")

    except Exception as e:
        logger.error(f"Ошибка при публикации сообщения в RabbitMQ: {e}")
        raise e


async def send_message_to_queue(channel_name: str, message_data: dict):
    """Функция для отправки сообщения в очередь"""
    try:
        logger.debug(f"Сообщение направлено в очередь {channel_name}: {message_data}")
        await publish_message_to_queue(
            queue_name=f"{channel_name}_messages", 
            message_data=message_data
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в очередь: {e}")
        raise e

async def handle_user_activity(
    action: str, username: str, channel_name: str, current_time: str
):
    """Обработчик действий пользователя в чате"""
    logger.debug(f"Обработка действий пользователя: {action} для пользователя {username} в канале {channel_name} в {current_time}")
    await send_message_to_queue(
        channel_name, 
        {"action": action, "username": username, "channel": channel_name, "time": current_time}
    )

async def handle_moderator_action(
    action: str, target_username: str, channel_name: str, current_time: str
):
    logger.debug(f"Обработка действий модератора: {action} для пользователя {target_username} в канале {channel_name} в {current_time}")
    await send_message_to_queue(
        channel_name, 
        {"action": action, "username": target_username, "channel": channel_name, "time": current_time}
    )
