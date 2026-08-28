from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import ChatMemberUpdated, Message

from .config import Settings
from .desk import TicketDesk
from .staff import IsSupportStaff
from .throttling import CustomerFloodMiddleware


async def handle_customer_start(message: Message, desk: TicketDesk) -> None:
    await desk.greet_customer(message)


async def handle_customer_close(message: Message, desk: TicketDesk) -> None:
    await desk.close_by_customer(message)


async def handle_customer_message(message: Message, desk: TicketDesk) -> None:
    await desk.forward_from_customer(message)


async def handle_agent_close(message: Message, desk: TicketDesk) -> None:
    await desk.close_by_agent(message)


async def handle_agent_message(message: Message, desk: TicketDesk) -> None:
    await desk.forward_from_agent(message)


async def handle_bot_membership_change(event: ChatMemberUpdated, desk: TicketDesk) -> None:
    await desk.leave_foreign_chat(event)


def create_router(settings: Settings) -> Router:
    customer_router = Router(name="customer")
    customer_router.message.filter(F.chat.type == ChatType.PRIVATE, F.from_user)
    if settings.customer_messages_per_minute > 0:
        customer_router.message.middleware(
            CustomerFloodMiddleware(settings.customer_messages_per_minute, settings.texts.slow_down)
        )
    customer_router.message.register(handle_customer_start, CommandStart())
    customer_router.message.register(handle_customer_close, Command("close"))
    customer_router.message.register(handle_customer_message)

    support_router = Router(name="support")
    support_router.message.filter(IsSupportStaff())
    support_router.message.register(handle_agent_close, Command("close"), F.is_topic_message)
    support_router.message.register(handle_agent_message, F.is_topic_message)

    root_router = Router(name="supportx")
    root_router.my_chat_member.register(handle_bot_membership_change)
    root_router.include_routers(customer_router, support_router)
    return root_router
