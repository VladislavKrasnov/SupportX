import asyncio
from typing import Any
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
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

@user_router.message(Command("close"), F.chat.type == ChatType.PRIVATE)
async def process_close_command(message: Message, bot: Bot, db_client: DatabaseClient, logger: Any) -> None:
    user_id = message.from_user.id
    topic_id = await db_client.retrieve_topic_for_user(user_id)
    if topic_id:
        await db_client.remove_topic_link(user_id)
        try:
            await bot.close_forum_topic(chat_id=config.support_group_id, message_thread_id=topic_id)
        except Exception:
            pass
        await message.answer(config.msg_ticket_closed)
        logger.info("User closed their topic", user_id=user_id, topic_id=topic_id)
    else:
        await message.answer("У вас нет открытого обращения.")

@user_router.message(F.chat.type == ChatType.PRIVATE)
async def relay_user_message(message: Message, bot: Bot, db_client: DatabaseClient, logger: Any) -> None:
    user_id = message.from_user.id
    
    if await db_client.is_user_banned(user_id):
        return

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
            
            username_text = f"@{message.from_user.username}" if message.from_user.username else "нет"
            commands_text = "Доступные команды:\n/close - закрыть тикет\n/ban - заблокировать\n/info - инфо"
            text = f"Информация о пользователе:\nID: <code>{user_id}</code>\nUsername: {username_text}\n\n{commands_text}"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Открыть диалог", url=f"tg://openmessage?user_id={user_id}")
            ]])
            msg = await bot.send_message(
                chat_id=config.support_group_id,
                message_thread_id=topic_id,
                text=text,
                reply_markup=kb
            )
            try:
                await bot.pin_chat_message(chat_id=config.support_group_id, message_id=msg.message_id)
            except Exception as e:
                logger.error("Failed to pin message", error=str(e), topic_id=topic_id)

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

@group_router.message(Command("ban"), F.chat.type == ChatType.SUPERGROUP, F.message_thread_id.is_not(None))
async def process_ban_command(message: Message, bot: Bot, db_client: DatabaseClient, logger: Any) -> None:
    topic_id = message.message_thread_id
    user_id = await db_client.retrieve_user_for_topic(topic_id)
    if not user_id:
        return
        
    await db_client.ban_user(user_id)
    logger.info("Admin banned user", admin_id=message.from_user.id, user_id=user_id)
    await message.answer(f"Пользователь <code>{user_id}</code> был заблокирован.")

@group_router.message(Command("info"), F.chat.type == ChatType.SUPERGROUP, F.message_thread_id.is_not(None))
async def process_info_command(message: Message, bot: Bot, db_client: DatabaseClient, logger: Any) -> None:
    topic_id = message.message_thread_id
    user_id = await db_client.retrieve_user_for_topic(topic_id)
    if not user_id:
        return
        
    try:
        user_info = await bot.get_chat(user_id)
        username_text = f"@{user_info.username}" if user_info.username else "нет"
    except Exception:
        username_text = "неизвестно"
        
    commands_text = "Доступные команды:\n/close - закрыть тикет\n/ban - заблокировать\n/info - инфо"
    text = f"Информация о пользователе:\nID: <code>{user_id}</code>\nUsername: {username_text}\n\n{commands_text}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть диалог", url=f"tg://openmessage?user_id={user_id}")
    ]])
    await message.answer(text, reply_markup=kb)

@group_router.message(Command("unban"), F.chat.type == ChatType.SUPERGROUP)
async def process_unban_command(message: Message, db_client: DatabaseClient, logger: Any) -> None:
    args = message.text.split() if message.text else []
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /unban <user_id>")
        return
        
    user_id = int(args[1])
    await db_client.unban_user(user_id)
    logger.info("Admin unbanned user", admin_id=message.from_user.id, user_id=user_id)
    await message.answer(f"Пользователь <code>{user_id}</code> был разблокирован.")

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
