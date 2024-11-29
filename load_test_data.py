import random
from uuid import uuid4
from datetime import datetime, timezone
from faker import Faker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.db import get_session
from apps.users.models.users import UserInDB
from apps.chats.models.chats import ChatInDB, UserChatLink, ChatMessageInDB
from apps.auth.models.auth_service import AuthTokensInDB

fake = Faker()


async def generate_users(session: AsyncSession, num_users: int = 20):
    """Генерация рандомных юзеров"""
    for _ in range(num_users):
        user_data = {
            'id': uuid4(),
            'username': fake.user_name()[:15],
            'email': fake.email()[:50],
            'hashed_pass': UserInDB.hash_password(fake.password()),
            'phone': fake.phone_number()[:15],
            'role': random.choice(['user', 'moderator'])[:15],
            'updated_at': datetime.now(timezone.utc),
        }
        stmt = insert(UserInDB).values(**user_data).on_conflict_do_nothing(index_elements=['email'])
        await session.execute(stmt)

    await session.commit()

async def generate_chats(session: AsyncSession, num_chats: int = 10):
    """Генерация рандомных чатов"""
    for _ in range(num_chats):
        chat_name = fake.word()[:50]
        chat = ChatInDB(
            id=uuid4(),
            name=chat_name
        )
        session.add(chat)
    
    await session.commit()

async def generate_user_chat_links(session: AsyncSession, num_links: int = 20):
    """Генерация рандомных связей юзеров с чатами"""
    users = await session.execute(select(UserInDB))
    users = users.scalars().all()

    chats = await session.execute(select(ChatInDB))
    chats = chats.scalars().all()

    for _ in range(num_links):
        user = random.choice(users)
        chat = random.choice(chats)


        stmt = insert(UserChatLink).values(
            user_id=user.id,
            chat_id=chat.id,
            joined_at=datetime.now(timezone.utc)
        ).on_conflict_do_nothing(index_elements=['user_id', 'chat_id'])
        await session.execute(stmt)

    await session.commit()

async def generate_messages(session: AsyncSession, num_messages: int = 30):
    """Генерация рандомных сообщений в чатах"""
    chats = (await session.execute(select(ChatInDB))).scalars().all()
    users = (await session.execute(select(UserInDB))).scalars().all()

    messages_to_add = []
    for _ in range(num_messages):
        chat = random.choice(chats)
        user = random.choice(users)

        message_data = {
            'id': uuid4(),
            'action': 'message',
            'username': user.username,
            'channel': chat.name,
            'time': datetime.now(timezone.utc),
            'sequence_number': random.randint(1, 1000),
            'message': fake.text(max_nb_chars=200),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        messages_to_add.append(ChatMessageInDB(**message_data))

    session.add_all(messages_to_add)
    await session.commit()

async def generate_refresh_tokens(session: AsyncSession, num_tokens: int = 30):
    """Генерация рандомных refresh-токенов"""
    async with session.begin():
        users = (await session.execute(select(UserInDB))).scalars().all()
        for user in users[:num_tokens]:
            refresh_token = str(uuid4())
            await AuthTokensInDB.save_refresh_token(session, user.id, refresh_token)

async def load_test_data(session: AsyncSession):
    """Загрузка тестовых данных в базу"""
    await generate_users(session)
    await generate_chats(session)
    await generate_user_chat_links(session)
    await generate_messages(session)
    await generate_refresh_tokens(session)

async def run():
    async for session in get_session():
        await load_test_data(session)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())