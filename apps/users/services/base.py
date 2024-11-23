from abc import ABC
from logging import ERROR
from typing import Any

from backoff import expo, on_exception
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class Base(ABC):
    def __init__(
        self,
        session: AsyncSession
    ) -> None:
        self.session: AsyncSession = session

    @property
    def client(self) -> AsyncClient:
        return AsyncClient()
    
    @on_exception(
        wait_gen=expo,
        exception=(
            Exception,
        ),
        max_tries=5,
        backoff_log_level=ERROR,
    )
    async def _create_one(self, instance: Any) -> Any:
        self.session.add(instance=instance)
        await self.session.commit()
        await self.session.refresh(instance=instance)
        return instance