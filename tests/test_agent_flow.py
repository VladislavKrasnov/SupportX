from unittest.mock import MagicMock

import pytest
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramForbiddenError

from tests.conftest import AGENT_ID, CUSTOMER_ID, SUPPORT_GROUP_ID, TOPIC_ID


def membership_change(chat_id: int, status: ChatMemberStatus) -> MagicMock:
    event = MagicMock()
    event.chat.id = chat_id
    event.chat.type = ChatType.SUPERGROUP
    event.new_chat_member.status = status
    return event


async def test_bot_leaves_foreign_group(desk, bot):
    await desk.leave_foreign_chat(membership_change(-1007, ChatMemberStatus.MEMBER))

    bot.leave_chat.assert_awaited_once_with(-1007)


@pytest.mark.parametrize(
    ("chat_id", "status"),
    [(SUPPORT_GROUP_ID, ChatMemberStatus.ADMINISTRATOR), (-1007, ChatMemberStatus.LEFT)],
)
async def test_bot_stays_in_support_group_and_ignores_removals(desk, bot, chat_id, status):
    await desk.leave_foreign_chat(membership_change(chat_id, status))

    bot.leave_chat.assert_not_awaited()


async def test_agent_reply_is_copied_to_customer(desk, bot, repository, agent_message):
    repository.touch_ticket_in_topic.return_value = CUSTOMER_ID

    await desk.forward_from_agent(agent_message)

    bot.copy_message.assert_awaited_once_with(chat_id=CUSTOMER_ID, from_chat_id=SUPPORT_GROUP_ID, message_id=1)


@pytest.mark.parametrize("text", ["// let me check with billing", "/unknown"])
async def test_internal_notes_and_commands_stay_in_topic(desk, bot, repository, agent_message, text):
    agent_message.text = text

    await desk.forward_from_agent(agent_message)

    repository.touch_ticket_in_topic.assert_not_awaited()
    bot.copy_message.assert_not_awaited()


async def test_internal_note_in_media_caption_stays_in_topic(desk, bot, agent_message):
    agent_message.text = None
    agent_message.caption = "// screenshot from logs"

    await desk.forward_from_agent(agent_message)

    bot.copy_message.assert_not_awaited()


async def test_customer_who_blocked_bot_gets_ticket_closed(desk, bot, repository, agent_message, settings):
    repository.touch_ticket_in_topic.return_value = CUSTOMER_ID
    bot.copy_message.side_effect = TelegramForbiddenError(method=MagicMock(), message="Forbidden: bot was blocked")

    await desk.forward_from_agent(agent_message)

    repository.close_ticket_in_topic.assert_awaited_once_with(TOPIC_ID)
    bot.send_message.assert_awaited_once_with(
        chat_id=SUPPORT_GROUP_ID, message_thread_id=TOPIC_ID, text=settings.texts.customer_blocked_bot_note
    )
    bot.close_forum_topic.assert_awaited_once_with(chat_id=SUPPORT_GROUP_ID, message_thread_id=TOPIC_ID)


async def test_agent_closes_ticket(desk, bot, repository, agent_message, settings):
    repository.close_ticket_in_topic.return_value = CUSTOMER_ID

    await desk.close_by_agent(agent_message)

    bot.send_message.assert_any_await(chat_id=CUSTOMER_ID, text=settings.texts.ticket_closed)
    bot.close_forum_topic.assert_awaited_once_with(chat_id=SUPPORT_GROUP_ID, message_thread_id=TOPIC_ID)
    bot.copy_message.assert_not_awaited()


async def test_agent_close_of_closed_ticket(desk, bot, repository, agent_message, settings):
    repository.close_ticket_in_topic.return_value = None

    await desk.close_by_agent(agent_message)

    agent_message.reply.assert_awaited_once_with(settings.texts.already_closed_note)
    bot.close_forum_topic.assert_not_awaited()
