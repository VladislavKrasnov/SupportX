import asyncio
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Filter
from aiogram.types import Message
from loguru import logger


class StaffDirectory:
    def __init__(self, bot: Bot, support_group_id: int, cache_ttl_seconds: float = 60) -> None:
        self._bot = bot
        self._support_group_id = support_group_id
        self._cache_ttl_seconds = cache_ttl_seconds
        self._admin_ids: frozenset[int] = frozenset()
        self._expires_at = 0.0
        self._refresh_lock = asyncio.Lock()

    async def authorizes(self, message: Message) -> bool:
        if message.chat.id != self._support_group_id:
            return False
        if message.sender_chat is not None:
            return message.sender_chat.id == self._support_group_id
        if message.from_user is None:
            return False
        try:
            admin_ids = await self._current_admin_ids()
        except TelegramAPIError as error:
            logger.error("Failed to load support group administrators: {}", error)
            return False
        return message.from_user.id in admin_ids

    async def _current_admin_ids(self) -> frozenset[int]:
        if time.monotonic() < self._expires_at:
            return self._admin_ids
        async with self._refresh_lock:
            if time.monotonic() >= self._expires_at:
                administrators = await self._bot.get_chat_administrators(self._support_group_id)
                self._admin_ids = frozenset(member.user.id for member in administrators)
                self._expires_at = time.monotonic() + self._cache_ttl_seconds
        return self._admin_ids


class IsSupportStaff(Filter):
    async def __call__(self, message: Message, staff: StaffDirectory) -> bool:
        return await staff.authorizes(message)
