import asyncio
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import config
from .database import DatabaseClient
from .middlewares import DatabaseMiddleware
from .handlers import user_router, group_router

from .scheduler import auto_close_topics_task

async def run_application() -> None:
    logger.remove()
    logger.add("logs.log", rotation="10 MB", compression="zip", serialize=True, level="INFO")
    logger.add(sys.stderr, level="INFO")
    
    logger.info("Initializing application...")

    db_client = DatabaseClient(config.database_url)
    await db_client.connect()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dispatcher = Dispatcher()
    dispatcher.message.middleware(DatabaseMiddleware(db_client))
    dispatcher.include_routers(user_router, group_router)
    
    scheduler_task = asyncio.create_task(auto_close_topics_task(bot, db_client, config))
    
    try:
        logger.info("Starting polling...")
        await dispatcher.start_polling(bot)
    finally:
        logger.info("Shutting down...")
        scheduler_task.cancel()
        await db_client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_application())
