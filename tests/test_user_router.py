import pytest
from unittest.mock import AsyncMock
from aiogram.exceptions import TelegramBadRequest
from bot.handlers import process_start_command, relay_user_message
from bot.config import config

@pytest.mark.asyncio
async def test_process_start_command(mock_db, mock_message, mock_logger):
    await process_start_command(mock_message, db_client=mock_db, logger=mock_logger)
    mock_db.register_user.assert_called_once_with(123)
    mock_message.answer.assert_called_once_with(config.msg_start)

@pytest.mark.asyncio
async def test_relay_user_message_new_topic(mock_db, mock_message, mock_bot, mock_logger):
    mock_db.retrieve_topic_for_user.return_value = None
    mock_topic = AsyncMock()
    mock_topic.message_thread_id = 456
    mock_bot.create_forum_topic.return_value = mock_topic
    
    await relay_user_message(mock_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    
    mock_db.register_user.assert_called_once_with(123)
    mock_bot.create_forum_topic.assert_called_once_with(
        chat_id=config.support_group_id,
        name="User 123"
    )
    mock_db.link_topic_to_user.assert_called_once_with(123, 456)
    mock_message.answer.assert_called_once_with(config.msg_ticket_created)
    mock_bot.copy_message.assert_called_once_with(
        chat_id=config.support_group_id,
        from_chat_id=123,
        message_id=1,
        message_thread_id=456
    )

@pytest.mark.asyncio
async def test_relay_user_message_topic_creation_failure(mock_db, mock_message, mock_bot, mock_logger):
    mock_db.retrieve_topic_for_user.return_value = None
    mock_bot.create_forum_topic.side_effect = TelegramBadRequest(
        method="createForumTopic",
        message="Bad Request: not enough rights"
    )
    
    await relay_user_message(mock_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    mock_message.answer.assert_called_once_with(config.msg_unsupported)
    mock_bot.copy_message.assert_not_called()

@pytest.mark.asyncio
async def test_relay_user_message_topic_deleted(mock_db, mock_message, mock_bot, mock_logger):
    mock_db.retrieve_topic_for_user.return_value = 456
    mock_bot.copy_message.side_effect = TelegramBadRequest(
        method="copyMessage",
        message="Bad Request: message thread not found"
    )
    
    await relay_user_message(mock_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    mock_db.remove_topic_link.assert_called_once_with(123)
    mock_message.answer.assert_called_once_with(config.msg_ticket_closed)
