from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot.handlers import create_router
from bot.staff import StaffDirectory
from tests.conftest import AGENT_ID, CUSTOMER_ID, SUPPORT_GROUP_ID, TOPIC_ID

MEMBER_ID = 555


@pytest.fixture
def desk() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def dispatch(desk, settings):
    bot = Bot(token="42:TEST")
    staff = StaffDirectory(bot, SUPPORT_GROUP_ID)
    staff._current_admin_ids = AsyncMock(return_value=frozenset({AGENT_ID}))
    dispatcher = Dispatcher(desk=desk, staff=staff)
    dispatcher.include_router(create_router(settings))
    update_id = 0

    async def feed(chat: dict, sender_id: int, text: str, thread_id: int | None = None) -> None:
        nonlocal update_id
        update_id += 1
        message = {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": chat,
            "from": {"id": sender_id, "is_bot": False, "first_name": "Someone"},
            "text": text,
        }
        if thread_id is not None:
            message |= {"message_thread_id": thread_id, "is_topic_message": True}
        if text.startswith("/"):
            message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
        await dispatcher.feed_update(bot, Update(update_id=update_id, message=message))

    yield feed
    await bot.session.close()


PRIVATE_CHAT = {"id": CUSTOMER_ID, "type": "private", "first_name": "Ann"}
SUPPORT_CHAT = {"id": SUPPORT_GROUP_ID, "type": "supergroup", "title": "Support", "is_forum": True}
FOREIGN_CHAT = {"id": -1007, "type": "supergroup", "title": "Elsewhere", "is_forum": True}


@pytest.mark.parametrize(
    ("text", "expected_method"),
    [("/start", "greet_customer"), ("/close", "close_by_customer"), ("hi", "forward_from_customer")],
)
async def test_customer_updates_are_routed(dispatch, desk, text, expected_method):
    await dispatch(PRIVATE_CHAT, CUSTOMER_ID, text)

    getattr(desk, expected_method).assert_awaited_once()


@pytest.mark.parametrize(
    ("text", "expected_method"),
    [
        ("/close", "close_by_agent"),
        ("/ban", "ban_customer"),
        ("/unban 42", "unban_customer"),
        ("/info", "show_customer_card"),
        ("hello", "forward_from_agent"),
    ],
)
async def test_agent_topic_updates_are_routed(dispatch, desk, text, expected_method):
    await dispatch(SUPPORT_CHAT, AGENT_ID, text, TOPIC_ID)

    getattr(desk, expected_method).assert_awaited_once()


async def test_unban_argument_is_passed(dispatch, desk):
    await dispatch(SUPPORT_CHAT, AGENT_ID, "/unban 42", TOPIC_ID)

    assert desk.unban_customer.await_args.args[1] == "42"


@pytest.mark.parametrize(
    ("chat", "sender_id"),
    [(SUPPORT_CHAT, MEMBER_ID), (FOREIGN_CHAT, AGENT_ID)],
)
@pytest.mark.parametrize("text", ["/close", "/ban", "/unban 42", "hello"])
async def test_untrusted_group_updates_are_ignored(dispatch, desk, chat, sender_id, text):
    await dispatch(chat, sender_id, text, TOPIC_ID)

    assert not desk.method_calls


async def test_customer_flood_is_dropped_with_single_warning(dispatch, desk, settings, monkeypatch):
    sent_answers = []

    async def record_answer(self, text, **_kwargs):
        sent_answers.append(text)

    monkeypatch.setattr("aiogram.types.Message.answer", record_answer)

    for _ in range(settings.customer_messages_per_minute + 5):
        await dispatch(PRIVATE_CHAT, CUSTOMER_ID, "spam")

    assert desk.forward_from_customer.await_count == settings.customer_messages_per_minute
    assert sent_answers == [settings.texts.slow_down]
