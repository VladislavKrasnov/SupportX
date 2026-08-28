import time
from collections.abc import Awaitable, Callable, Hashable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class FixedWindowCounter:
    def __init__(self, window_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._window_seconds = window_seconds
        self._clock = clock
        self._window_ends_at = 0.0
        self._hits: dict[Hashable, int] = {}

    def hit(self, key: Hashable) -> int:
        now = self._clock()
        if now >= self._window_ends_at:
            self._hits.clear()
            self._window_ends_at = now + self._window_seconds
        hits = self._hits.get(key, 0) + 1
        self._hits[key] = hits
        return hits


class CustomerFloodMiddleware(BaseMiddleware):
    def __init__(self, messages_per_minute: int, slow_down_text: str) -> None:
        self._messages_per_minute = messages_per_minute
        self._slow_down_text = slow_down_text
        self._counter = FixedWindowCounter(window_seconds=60)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        hits = self._counter.hit(event.chat.id)
        if hits <= self._messages_per_minute:
            return await handler(event, data)
        if hits == self._messages_per_minute + 1:
            await event.answer(self._slow_down_text)
        return None
