import asyncio
from typing import Any
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger as base_logger

from .config import config
from .database import DatabaseClient

user_router = Router()
group_router = Router()

@user_router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def process_start_command(message: Message, db_client: DatabaseClient, logger: Any) -> None:
    user_id = message.from_user.id
    await db_client.register_user(user_id)
    logger.info("User registered via /start", user_id=user_id)
    await message.answer(config.msg_start)

@user_router.message(F.chat.type == ChatType.PRIVATE)
async def relay_user_message(message: Message, bot: Bot, db_client: DatabaseClient, logger: Any) -> None:
    user_id = message.from_user.id
    
    topic_id = await db_client.retrieve_topic_for_user(user_id)
    if not topic_id:
        try:
            topic = await bot.create_forum_topic(
                chat_id=config.support_group_id,
                name=f"User {user_id}"
            )
            topic_id = topic.message_thread_id
            await db_client.register_user(user_id)
            await db_client.link_topic_to_user(user_id, topic_id)
            logger.info("Created new forum topic for user", user_id=user_id, topic_id=topic_id)
            await message.answer(config.msg_ticket_created)
        except TelegramBadRequest as e:
            logger.error("Failed to create forum topic", error=str(e), user_id=user_id)
            await message.answer(config.msg_unsupported)
            return

    try:
        await bot.copy_message(
            chat_id=config.support_group_id,
            from_chat_id=user_id,
            message_id=message.message_id,
            message_thread_id=topic_id
        )
    except TelegramBadRequest as e:
        if "message thread not found" in str(e).lower():
            logger.info("Topic was deleted, resetting link", user_id=user_id, topic_id=topic_id)
            await db_client.remove_topic_link(user_id)
            await message.answer(config.msg_ticket_closed)
        else:
            logger.error("Failed to copy user message", error=str(e), user_id=user_id)

@group_router.message(F.chat.type == ChatType.SUPERGROUP, F.message_thread_id.is_not(None))
async def relay_support_message(message: Message, bot: Bot, db_client: DatabaseClient, logger: Any) -> None:
    topic_id = message.message_thread_id
    user_id = await db_client.retrieve_user_for_topic(topic_id)
    
    if not user_id:
        return

    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=config.support_group_id,
            message_id=message.message_id
        )
    except TelegramForbiddenError:
        logger.warning("User blocked the bot, closing topic", user_id=user_id, topic_id=topic_id)
        await db_client.remove_topic_link(user_id)
        await bot.send_message(
            chat_id=config.support_group_id,
            message_thread_id=topic_id,
            text=config.msg_user_blocked
        )
        try:
            await bot.close_forum_topic(
                chat_id=config.support_group_id,
                message_thread_id=topic_id
            )
        except Exception:
            pass
