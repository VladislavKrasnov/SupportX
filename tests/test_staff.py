from unittest.mock import AsyncMock, MagicMock

from aiogram.enums import ChatType
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Chat, User

from bot.staff import StaffDirectory
from tests.conftest import AGENT_ID, SUPPORT_GROUP_ID, build_message

SUPPORT_CHAT = Chat(id=SUPPORT_GROUP_ID, type=ChatType.SUPERGROUP)


def build_directory(admin_ids: list[int]) -> tuple[StaffDirectory, AsyncMock]:
    bot = AsyncMock()
    bot.get_chat_administrators.return_value = [MagicMock(user=MagicMock(id=admin_id)) for admin_id in admin_ids]
    return StaffDirectory(bot, SUPPORT_GROUP_ID), bot


async def test_admin_of_support_group_is_authorized():
    directory, _ = build_directory([AGENT_ID])
    message = build_message(chat=SUPPORT_CHAT, from_user=User(id=AGENT_ID, is_bot=False, first_name="A"))

    assert await directory.authorizes(message)


async def test_regular_member_is_rejected():
    directory, _ = build_directory([AGENT_ID])
    message = build_message(chat=SUPPORT_CHAT, from_user=User(id=1, is_bot=False, first_name="M"))

    assert not await directory.authorizes(message)


async def test_foreign_group_is_rejected_without_api_calls():
    directory, bot = build_directory([AGENT_ID])
    foreign_chat = Chat(id=-1007, type=ChatType.SUPERGROUP)
    message = build_message(chat=foreign_chat, from_user=User(id=AGENT_ID, is_bot=False, first_name="A"))

    assert not await directory.authorizes(message)
    bot.get_chat_administrators.assert_not_awaited()


async def test_anonymous_admin_is_authorized_and_foreign_channel_is_not():
    directory, _ = build_directory([])
    bot_user = User(id=1087968824, is_bot=True, first_name="GroupAnonymousBot")
    anonymous_admin = build_message(chat=SUPPORT_CHAT, from_user=bot_user, sender_chat=SUPPORT_CHAT)
    foreign_channel = build_message(
        chat=SUPPORT_CHAT, from_user=bot_user, sender_chat=Chat(id=-1009, type=ChatType.CHANNEL)
    )

    assert await directory.authorizes(anonymous_admin)
    assert not await directory.authorizes(foreign_channel)


async def test_admin_list_is_cached():
    directory, bot = build_directory([AGENT_ID])
    message = build_message(chat=SUPPORT_CHAT, from_user=User(id=AGENT_ID, is_bot=False, first_name="A"))

    for _ in range(5):
        await directory.authorizes(message)

    bot.get_chat_administrators.assert_awaited_once()


async def test_unavailable_admin_list_denies_access():
    directory, bot = build_directory([AGENT_ID])
    bot.get_chat_administrators.side_effect = TelegramNetworkError(method=MagicMock(), message="timeout")
    message = build_message(chat=SUPPORT_CHAT, from_user=User(id=AGENT_ID, is_bot=False, first_name="A"))

    assert not await directory.authorizes(message)
