import pytest
from aiogram.exceptions import TelegramForbiddenError
from bot.handlers import relay_support_message
from bot.config import config

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
