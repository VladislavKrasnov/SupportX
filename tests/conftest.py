from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType
from aiogram.types import Chat, Message, User

from bot.config import Settings, Texts
from bot.desk import TicketDesk

SUPPORT_GROUP_ID = -100500
CUSTOMER_ID = 123
AGENT_ID = 999
TOPIC_ID = 456


@pytest.fixture
def settings() -> Settings:
    return Settings(
        bot_token="token",
        support_group_id=SUPPORT_GROUP_ID,
        database_url="postgresql://localhost/supportx",
        internal_note_prefix="//",
        customer_messages_per_minute=30,
        new_tickets_per_minute=2,
        log_level="INFO",
        texts=Texts(),
    )


@pytest.fixture
def bot() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def desk(bot: AsyncMock, repository: AsyncMock, settings: Settings) -> TicketDesk:
    return TicketDesk(bot, repository, settings)


def build_message(
    *,
    chat: Chat,
    from_user: User | None,
    text: str | None = "hello",
    message_thread_id: int | None = None,
    sender_chat: Chat | None = None,
) -> MagicMock:
    message = MagicMock(spec=Message)
    message.chat = chat
    message.from_user = from_user
    message.sender_chat = sender_chat
    message.text = text
    message.caption = None
    message.message_id = 1
    message.message_thread_id = message_thread_id
    message.is_topic_message = message_thread_id is not None
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def customer_message() -> MagicMock:
    return build_message(
        chat=Chat(id=CUSTOMER_ID, type=ChatType.PRIVATE),
        from_user=User(id=CUSTOMER_ID, is_bot=False, first_name="Ann", username="ann"),
    )


@pytest.fixture
def agent_message() -> MagicMock:
    return build_message(
        chat=Chat(id=SUPPORT_GROUP_ID, type=ChatType.SUPERGROUP, is_forum=True),
        from_user=User(id=AGENT_ID, is_bot=False, first_name="Agent"),
        message_thread_id=TOPIC_ID,
    )
