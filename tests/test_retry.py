from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import GetMe

from bot import retry
from bot.retry import RetryAfterMiddleware


def rate_limited(seconds: int) -> TelegramRetryAfter:
    return TelegramRetryAfter(method=GetMe(), message="Too Many Requests", retry_after=seconds)


@pytest.fixture(autouse=True)
def instant_sleep(monkeypatch) -> AsyncMock:
    sleep = AsyncMock()
    monkeypatch.setattr(retry.asyncio, "sleep", sleep)
    return sleep


async def test_request_is_retried_after_rate_limit(instant_sleep):
    make_request = AsyncMock(side_effect=[rate_limited(3), "ok"])

    response = await RetryAfterMiddleware()(make_request, MagicMock(), GetMe())

    assert response == "ok"
    instant_sleep.assert_awaited_once_with(3)


async def test_long_rate_limit_is_not_waited_out(instant_sleep):
    make_request = AsyncMock(side_effect=rate_limited(600))

    with pytest.raises(TelegramRetryAfter):
        await RetryAfterMiddleware(max_wait_seconds=60)(make_request, MagicMock(), GetMe())

    instant_sleep.assert_not_awaited()


async def test_retries_are_bounded():
    make_request = AsyncMock(side_effect=rate_limited(1))

    with pytest.raises(TelegramRetryAfter):
        await RetryAfterMiddleware(max_retries=2)(make_request, MagicMock(), GetMe())

    assert make_request.await_count == 3
