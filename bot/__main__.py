import asyncio
import sys
from contextlib import suppress

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from loguru import logger

from .config import ConfigurationError, load_settings
from .database import Repository
from .desk import TicketDesk
from .handlers import create_router
from .retry import RetryAfterMiddleware
from .schema import apply_migrations
from .staff import StaffDirectory
from .sweeper import close_inactive_tickets_forever


async def run_bot() -> None:
    load_dotenv()
    try:
        settings = load_settings()
    except ConfigurationError as error:
        sys.exit(f"Configuration error: {error}")
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)

    pool = await asyncpg.create_pool(settings.database_url)
    try:
        await apply_migrations(pool)

        bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        bot.session.middleware(RetryAfterMiddleware())
        desk = TicketDesk(bot, Repository(pool), settings)

        dispatcher = Dispatcher(desk=desk, staff=StaffDirectory(bot, settings.support_group_id))
        dispatcher.include_router(create_router(settings))

        sweeper_task = None
        if settings.auto_close_after_days > 0:
            sweeper_task = asyncio.create_task(close_inactive_tickets_forever(desk, settings.auto_close_after_days))
        try:
            await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
        finally:
            if sweeper_task is not None:
                sweeper_task.cancel()
                with suppress(asyncio.CancelledError):
                    await sweeper_task
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_bot())
