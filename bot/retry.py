import asyncio

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType
from loguru import logger


class RetryAfterMiddleware(BaseRequestMiddleware):
    def __init__(self, max_retries: int = 3, max_wait_seconds: int = 60) -> None:
        self._max_retries = max_retries
        self._max_wait_seconds = max_wait_seconds

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        for _ in range(self._max_retries):
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as error:
                if error.retry_after > self._max_wait_seconds:
                    raise
                logger.warning("Telegram rate limit hit on {}, retrying in {}s", method.__api_method__, error.retry_after)
                await asyncio.sleep(error.retry_after)
        return await make_request(bot, method)
