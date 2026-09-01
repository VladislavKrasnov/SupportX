import asyncio
from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramBadRequest

from bot.database import CustomerState
from tests.conftest import CUSTOMER_ID, SUPPORT_GROUP_ID, TOPIC_ID


def bad_request(text: str) -> TelegramBadRequest:
    return TelegramBadRequest(method=MagicMock(), message=f"Bad Request: {text}")


async def test_greeting_registers_customer(desk, repository, customer_message, settings):
    await desk.greet_customer(customer_message)

    repository.register_customer.assert_awaited_once_with(CUSTOMER_ID)
    customer_message.answer.assert_awaited_once_with(settings.texts.welcome)


async def test_message_to_open_ticket_is_copied_without_extra_calls(desk, bot, repository, customer_message):
    repository.touch_open_ticket.return_value = TOPIC_ID

    await desk.forward_from_customer(customer_message)

    repository.fetch_customer_state.assert_not_awaited()
    bot.create_forum_topic.assert_not_awaited()
    bot.copy_message.assert_awaited_once_with(
        chat_id=SUPPORT_GROUP_ID, from_chat_id=CUSTOMER_ID, message_id=1, message_thread_id=TOPIC_ID
    )
    customer_message.answer.assert_not_awaited()


async def test_first_message_starts_topic_with_pinned_card(desk, bot, repository, customer_message, settings):
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=None)
    bot.create_forum_topic.return_value = MagicMock(message_thread_id=TOPIC_ID)
    bot.send_message.return_value = MagicMock(message_id=77)

    await desk.forward_from_customer(customer_message)

    bot.create_forum_topic.assert_awaited_once_with(chat_id=SUPPORT_GROUP_ID, name=f"Ann · {CUSTOMER_ID}")
    repository.bind_topic.assert_awaited_once_with(CUSTOMER_ID, TOPIC_ID)
    card_text = bot.send_message.await_args.kwargs["text"]
    assert f"<code>{CUSTOMER_ID}</code>" in card_text and "@ann" in card_text
    bot.pin_chat_message.assert_awaited_once_with(chat_id=SUPPORT_GROUP_ID, message_id=77, disable_notification=True)
    customer_message.answer.assert_awaited_once_with(settings.texts.ticket_opened)
    bot.copy_message.assert_awaited_once()


async def test_customer_card_escapes_html_in_names(desk, bot, repository, customer_message):
    customer_message.from_user = customer_message.from_user.model_copy(update={"first_name": "<b>x</b>"})
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=None)
    bot.create_forum_topic.return_value = MagicMock(message_thread_id=TOPIC_ID)

    await desk.forward_from_customer(customer_message)

    assert "&lt;b&gt;x&lt;/b&gt;" in bot.send_message.await_args.kwargs["text"]


async def test_concurrent_first_messages_start_single_topic(desk, bot, repository, customer_message):
    bound_topic: list[int] = []

    async def touch_open_ticket(_user_id):
        return bound_topic[0] if bound_topic else None

    async def create_forum_topic(**_kwargs):
        await asyncio.sleep(0.01)
        return MagicMock(message_thread_id=TOPIC_ID)

    async def bind_topic(_user_id, topic_id):
        bound_topic.append(topic_id)

    repository.touch_open_ticket.side_effect = touch_open_ticket
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=None)
    repository.bind_topic.side_effect = bind_topic
    bot.create_forum_topic.side_effect = create_forum_topic

    await asyncio.gather(*(desk.forward_from_customer(customer_message) for _ in range(3)))

    assert bot.create_forum_topic.await_count == 1
    assert bot.copy_message.await_count == 3


async def test_banned_customer_is_ignored(desk, bot, repository, customer_message):
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=True, topic_id=TOPIC_ID)

    await desk.forward_from_customer(customer_message)

    bot.copy_message.assert_not_awaited()
    bot.reopen_forum_topic.assert_not_awaited()
    customer_message.answer.assert_not_awaited()


async def test_returning_customer_reuses_closed_topic(desk, bot, repository, customer_message, settings):
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=TOPIC_ID)

    await desk.forward_from_customer(customer_message)

    bot.reopen_forum_topic.assert_awaited_once_with(chat_id=SUPPORT_GROUP_ID, message_thread_id=TOPIC_ID)
    repository.reopen_ticket.assert_awaited_once_with(CUSTOMER_ID)
    bot.create_forum_topic.assert_not_awaited()
    customer_message.answer.assert_awaited_once_with(settings.texts.ticket_opened)
    assert bot.copy_message.await_args.kwargs["message_thread_id"] == TOPIC_ID


async def test_returning_customer_gets_new_topic_when_old_one_was_deleted(desk, bot, repository, customer_message):
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=TOPIC_ID)
    bot.reopen_forum_topic.side_effect = bad_request("TOPIC_ID_INVALID")
    bot.create_forum_topic.return_value = MagicMock(message_thread_id=789)

    await desk.forward_from_customer(customer_message)

    repository.bind_topic.assert_awaited_once_with(CUSTOMER_ID, 789)
    assert bot.copy_message.await_args.kwargs["message_thread_id"] == 789


async def test_message_is_redelivered_when_open_topic_was_deleted(desk, bot, repository, customer_message):
    repository.touch_open_ticket.return_value = TOPIC_ID
    bot.copy_message.side_effect = [bad_request("message thread not found"), None]
    bot.create_forum_topic.return_value = MagicMock(message_thread_id=789)

    await desk.forward_from_customer(customer_message)

    repository.bind_topic.assert_awaited_once_with(CUSTOMER_ID, 789)
    assert bot.copy_message.await_count == 2
    assert bot.copy_message.await_args.kwargs["message_thread_id"] == 789


async def test_topic_creation_failure_reports_to_customer(desk, bot, repository, customer_message, settings):
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=None)
    bot.create_forum_topic.side_effect = bad_request("not enough rights to create a topic")

    await desk.forward_from_customer(customer_message)

    bot.copy_message.assert_not_awaited()
    customer_message.answer.assert_awaited_once_with(settings.texts.delivery_failed)


async def test_customer_closes_open_ticket(desk, bot, repository, customer_message, settings):
    repository.close_ticket_of_customer.return_value = TOPIC_ID

    await desk.close_by_customer(customer_message)

    customer_message.answer.assert_awaited_once_with(settings.texts.ticket_closed)
    bot.send_message.assert_awaited_once_with(
        chat_id=SUPPORT_GROUP_ID, message_thread_id=TOPIC_ID, text=settings.texts.closed_by_customer_note
    )
    bot.close_forum_topic.assert_awaited_once_with(chat_id=SUPPORT_GROUP_ID, message_thread_id=TOPIC_ID)


async def test_customer_close_without_ticket(desk, bot, repository, customer_message, settings):
    repository.close_ticket_of_customer.return_value = None

    await desk.close_by_customer(customer_message)

    customer_message.answer.assert_awaited_once_with(settings.texts.no_open_ticket)
    bot.close_forum_topic.assert_not_awaited()


async def test_customer_lock_is_released_after_use(desk, repository, customer_message):
    repository.touch_open_ticket.return_value = TOPIC_ID

    await desk.forward_from_customer(customer_message)

    assert len(desk._customer_locks) == 0


async def test_new_tickets_beyond_limit_are_postponed(desk, bot, repository, customer_message, settings):
    repository.touch_open_ticket.return_value = None
    repository.fetch_customer_state.return_value = CustomerState(is_banned=False, topic_id=None)
    bot.create_forum_topic.return_value = MagicMock(message_thread_id=TOPIC_ID)

    for _ in range(settings.new_tickets_per_minute + 1):
        await desk.forward_from_customer(customer_message)

    assert bot.create_forum_topic.await_count == settings.new_tickets_per_minute
    customer_message.answer.assert_awaited_with(settings.texts.desk_busy)
