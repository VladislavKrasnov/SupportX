from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger
from bot.database import DatabaseClient

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db_client: DatabaseClient):
        self.db_client = db_client
        self.logger = logger

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["db_client"] = self.db_client
        data["logger"] = self.logger
        return await handler(event, data)
