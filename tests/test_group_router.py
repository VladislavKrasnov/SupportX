import pytest
from aiogram.exceptions import TelegramForbiddenError
from bot.handlers import relay_support_message, process_ban_command, process_unban_command, process_info_command
from bot.config import config
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_relay_support_message_success(mock_db, mock_group_message, mock_bot, mock_logger):
    mock_db.retrieve_user_for_topic.return_value = 123
    
    await relay_support_message(mock_group_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    
    mock_bot.copy_message.assert_called_once_with(
        chat_id=123,
        from_chat_id=config.support_group_id,
        message_id=2
    )

@pytest.mark.asyncio
async def test_relay_support_message_user_blocked(mock_db, mock_group_message, mock_bot, mock_logger):
    mock_db.retrieve_user_for_topic.return_value = 123
    mock_bot.copy_message.side_effect = TelegramForbiddenError(
        method="copyMessage",
        message="Forbidden: bot was blocked by the user"
    )
    
    await relay_support_message(mock_group_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    
    mock_db.remove_topic_link.assert_called_once_with(123)
    mock_bot.send_message.assert_called_once_with(
        chat_id=config.support_group_id,
        message_thread_id=456,
        text=config.msg_user_blocked
    )
    mock_bot.close_forum_topic.assert_called_once_with(
        chat_id=config.support_group_id,
        message_thread_id=456
    )

@pytest.mark.asyncio
async def test_process_ban_command(mock_db, mock_group_message, mock_bot, mock_logger):
    mock_db.retrieve_user_for_topic.return_value = 123
    await process_ban_command(mock_group_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    mock_db.ban_user.assert_called_once_with(123)
    mock_group_message.answer.assert_called_once()

@pytest.mark.asyncio
async def test_process_unban_command(mock_db, mock_group_message, mock_logger):
    mock_group_message.text = "/unban 123"
    await process_unban_command(mock_group_message, db_client=mock_db, logger=mock_logger)
    mock_db.unban_user.assert_called_once_with(123)
    mock_group_message.answer.assert_called_once()

@pytest.mark.asyncio
async def test_process_info_command(mock_db, mock_group_message, mock_bot, mock_logger):
    mock_db.retrieve_user_for_topic.return_value = 123
    mock_user_info = AsyncMock()
    mock_user_info.username = "testuser"
    mock_bot.get_chat.return_value = mock_user_info
    
    await process_info_command(mock_group_message, bot=mock_bot, db_client=mock_db, logger=mock_logger)
    mock_bot.get_chat.assert_called_once_with(123)
    mock_group_message.answer.assert_called_once()
