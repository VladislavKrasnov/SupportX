import asyncio
from aiogram import Bot
from loguru import logger
from .database import DatabaseClient
from .config import Config

async def auto_close_topics_task(bot: Bot, db_client: DatabaseClient, config: Config) -> None:
    if config.auto_close_topics_days <= 0:
        logger.info("Auto-close topics is disabled.")
        return

    logger.info("Starting auto-close topics task...")
    while True:
        try:
            expired_topics = await db_client.get_expired_topics(config.auto_close_topics_days)
            for user_id, topic_id in expired_topics:
                logger.info("Auto-closing expired topic", user_id=user_id, topic_id=topic_id)
                try:
                    await bot.close_forum_topic(chat_id=config.support_group_id, message_thread_id=topic_id)
                except Exception as e:
                    logger.error("Failed to close forum topic in telegram", error=str(e), topic_id=topic_id)
                
                await db_client.remove_topic_link(user_id)
                
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=config.msg_ticket_closed
                    )
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error("Error in auto-close topics task", error=str(e))
            
        await asyncio.sleep(3600)  # Check every hour
