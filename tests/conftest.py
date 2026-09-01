import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType
from bot.config import config

@pytest.fixture
def mock_bot():
    return AsyncMock()

@pytest.fixture
def mock_message():
    message = AsyncMock(spec=Message)
    message.from_user = User(id=123, is_bot=False, first_name="Test")
    message.chat = Chat(id=123, type=ChatType.PRIVATE)
    message.message_id = 1
    message.content_type = "text"
    message.answer = AsyncMock()
    return message

@pytest.fixture
def mock_group_message():
    message = AsyncMock(spec=Message)
    message.chat = Chat(id=config.support_group_id, type=ChatType.SUPERGROUP)
    message.from_user = User(id=999, is_bot=False, first_name="Admin")
    message.message_thread_id = 456
    message.message_id = 2
    message.content_type = "text"
    message.answer = AsyncMock()
    return message

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.register_user = AsyncMock()
    mock.retrieve_topic_for_user = AsyncMock()
    mock.link_topic_to_user = AsyncMock()
    mock.remove_topic_link = AsyncMock()
    mock.retrieve_user_for_topic = AsyncMock()
    mock.is_user_banned.return_value = False
    return mock

from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_logger():
    return MagicMock()
