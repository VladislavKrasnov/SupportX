import asyncio
from contextlib import suppress
from html import escape
from weakref import WeakValueDictionary

from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from loguru import logger

from .config import Settings
from .database import Repository
from .throttling import FixedWindowCounter

MISSING_TOPIC_ERROR_MARKERS = ("message thread not found", "topic_id_invalid", "topic_deleted")
TOPIC_NOT_MODIFIED_ERROR_MARKER = "topic_not_modified"
TOPIC_TITLE_MAX_LENGTH = 128
NEW_TICKETS_WINDOW_KEY = "new_tickets"
PRESENT_MEMBER_STATUSES = frozenset({ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR})


class DeskBusyError(Exception):
    pass


def is_missing_topic_error(error: TelegramBadRequest) -> bool:
    error_text = error.message.lower()
    return any(marker in error_text for marker in MISSING_TOPIC_ERROR_MARKERS)


class TicketDesk:
    def __init__(self, bot: Bot, repository: Repository, settings: Settings) -> None:
        self._bot = bot
        self._repository = repository
        self._support_group_id = settings.support_group_id
        self._internal_note_prefix = settings.internal_note_prefix
        self._texts = settings.texts
        self._new_tickets_per_minute = settings.new_tickets_per_minute
        self._new_tickets_counter = FixedWindowCounter(window_seconds=60)
        self._customer_locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()

    async def greet_customer(self, message: Message) -> None:
        await self._repository.register_customer(message.from_user.id)
        await message.answer(self._texts.welcome)

    async def forward_from_customer(self, message: Message) -> None:
        customer = message.from_user
        async with self._lock_for(customer.id):
            try:
                topic_id = await self._resolve_open_topic(customer, message)
                try:
                    await self._copy_to_topic(message, topic_id)
                except TelegramBadRequest as error:
                    if not is_missing_topic_error(error):
                        raise
                    logger.warning("Topic {} of customer {} is gone, starting a new one", topic_id, customer.id)
                    topic_id = await self._start_topic(customer)
                    await self._copy_to_topic(message, topic_id)
            except DeskBusyError:
                logger.warning("New ticket limit reached, customer {} asked to retry later", customer.id)
                await message.answer(self._texts.desk_busy)
            except TelegramAPIError as error:
                logger.error("Failed to forward message of customer {}: {}", customer.id, error)
                await message.answer(self._texts.delivery_failed)

    async def close_by_customer(self, message: Message) -> None:
        customer_id = message.from_user.id
        async with self._lock_for(customer_id):
            topic_id = await self._repository.close_ticket_of_customer(customer_id)
        if topic_id is None:
            await message.answer(self._texts.no_open_ticket)
            return
        await message.answer(self._texts.ticket_closed)
        await self._archive_topic(topic_id, self._texts.closed_by_customer_note)
        logger.info("Customer {} closed ticket in topic {}", customer_id, topic_id)

    async def forward_from_agent(self, message: Message) -> None:
        if self._is_internal(message):
            return
        topic_id = message.message_thread_id
        customer_id = await self._repository.touch_ticket_in_topic(topic_id)
        if customer_id is None:
            return
        try:
            await self._bot.copy_message(
                chat_id=customer_id,
                from_chat_id=self._support_group_id,
                message_id=message.message_id,
            )
        except TelegramForbiddenError:
            logger.info("Customer {} blocked the bot, closing topic {}", customer_id, topic_id)
            await self._repository.close_ticket_in_topic(topic_id)
            await self._archive_topic(topic_id, self._texts.customer_blocked_bot_note)
        except TelegramBadRequest as error:
            logger.warning("Failed to deliver agent message to customer {}: {}", customer_id, error)
            await message.reply(self._texts.not_delivered_note)

    async def close_by_agent(self, message: Message) -> None:
        topic_id = message.message_thread_id
        customer_id = await self._repository.close_ticket_in_topic(topic_id)
        if customer_id is None:
            await message.reply(self._texts.already_closed_note)
            return
        await self._notify_customer(customer_id, self._texts.ticket_closed)
        await self._archive_topic(topic_id, self._texts.closed_by_agent_note)
        logger.info("Agent {} closed ticket in topic {}", message.from_user.id, topic_id)

    async def _resolve_open_topic(self, customer: User, message: Message) -> int:
        topic_id = await self._repository.touch_open_ticket(customer.id)
        if topic_id is not None:
            return topic_id
        previous_topic_id = await self._repository.find_topic_of_customer(customer.id)
        if previous_topic_id is None:
            topic_id = await self._start_topic(customer)
        else:
            topic_id = await self._reopen_topic(customer, previous_topic_id)
        await message.answer(self._texts.ticket_opened)
        return topic_id

    async def leave_foreign_chat(self, event: ChatMemberUpdated) -> None:
        if event.chat.type == ChatType.PRIVATE or event.chat.id == self._support_group_id:
            return
        if event.new_chat_member.status not in PRESENT_MEMBER_STATUSES:
            return
        logger.warning("Leaving chat {} the bot was added to by {}", event.chat.id, event.from_user.id)
        with suppress(TelegramAPIError):
            await self._bot.leave_chat(event.chat.id)

    async def _start_topic(self, customer: User) -> int:
        if (
            self._new_tickets_per_minute > 0
            and self._new_tickets_counter.hit(NEW_TICKETS_WINDOW_KEY) > self._new_tickets_per_minute
        ):
            raise DeskBusyError
        topic_title = self._texts.topic_title.format(
            full_name=customer.full_name,
            user_id=customer.id,
            username=customer.username or "",
            note_prefix=self._internal_note_prefix,
        )
        topic = await self._bot.create_forum_topic(
            chat_id=self._support_group_id,
            name=topic_title[:TOPIC_TITLE_MAX_LENGTH],
        )
        topic_id = topic.message_thread_id
        await self._repository.bind_topic(customer.id, topic_id)
        await self._post_customer_card(customer, topic_id)
        logger.info("Opened topic {} for customer {}", topic_id, customer.id)
        return topic_id

    async def _post_customer_card(self, customer: User, topic_id: int) -> None:
        text, keyboard = self._render_customer_card(customer.id, customer.full_name, customer.username)
        try:
            card = await self._bot.send_message(
                chat_id=self._support_group_id,
                message_thread_id=topic_id,
                text=text,
                reply_markup=keyboard,
            )
            await self._bot.pin_chat_message(
                chat_id=self._support_group_id,
                message_id=card.message_id,
                disable_notification=True,
            )
        except TelegramBadRequest as error:
            logger.warning("Failed to post customer card to topic {}: {}", topic_id, error)

    async def _reopen_topic(self, customer: User, topic_id: int) -> int:
        try:
            await self._bot.reopen_forum_topic(chat_id=self._support_group_id, message_thread_id=topic_id)
        except TelegramBadRequest as error:
            if is_missing_topic_error(error):
                return await self._start_topic(customer)
            if TOPIC_NOT_MODIFIED_ERROR_MARKER not in error.message.lower():
                raise
        await self._repository.reopen_ticket(customer.id)
        await self._post_to_topic(topic_id, self._texts.ticket_reopened_note)
        logger.info("Reopened topic {} for customer {}", topic_id, customer.id)
        return topic_id

    async def _copy_to_topic(self, message: Message, topic_id: int) -> None:
        await self._bot.copy_message(
            chat_id=self._support_group_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            message_thread_id=topic_id,
        )

    async def _archive_topic(self, topic_id: int, note: str) -> None:
        await self._post_to_topic(topic_id, note)
        with suppress(TelegramBadRequest):
            await self._bot.close_forum_topic(chat_id=self._support_group_id, message_thread_id=topic_id)

    async def _post_to_topic(self, topic_id: int, text: str) -> None:
        with suppress(TelegramBadRequest):
            await self._bot.send_message(chat_id=self._support_group_id, message_thread_id=topic_id, text=text)

    async def _notify_customer(self, customer_id: int, text: str) -> None:
        with suppress(TelegramForbiddenError, TelegramBadRequest):
            await self._bot.send_message(chat_id=customer_id, text=text)

    def _render_customer_card(
        self, customer_id: int, full_name: str, username: str | None
    ) -> tuple[str, InlineKeyboardMarkup]:
        text = self._texts.customer_card.format(
            full_name=escape(full_name),
            user_id=customer_id,
            username=f"@{escape(username)}" if username else self._texts.no_username,
            note_prefix=escape(self._internal_note_prefix),
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=self._texts.open_chat_button, url=f"tg://openmessage?user_id={customer_id}")]
            ]
        )
        return text, keyboard

    def _is_internal(self, message: Message) -> bool:
        content = message.text or message.caption or ""
        if content.startswith("/"):
            return True
        return bool(self._internal_note_prefix) and content.startswith(self._internal_note_prefix)

    def _lock_for(self, customer_id: int) -> asyncio.Lock:
        lock = self._customer_locks.get(customer_id)
        if lock is None:
            lock = self._customer_locks[customer_id] = asyncio.Lock()
        return lock
