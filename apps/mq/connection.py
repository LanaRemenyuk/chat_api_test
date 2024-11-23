import aio_pika

class RabbitMQConnectionManager:
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.connection = None
        self.channel = None

    async def connect(self):
        if not self.connection:
            self.connection = await aio_pika.connect_robust(self.broker_url)
            self.channel = await self.connection.channel()
        return self.channel

    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
