import asyncio

from loguru import logger

from .desk import TicketDesk

SWEEP_INTERVAL_SECONDS = 3600


async def close_inactive_tickets_forever(desk: TicketDesk, inactive_days: int) -> None:
    while True:
        try:
            closed_count = await desk.close_inactive_tickets(inactive_days)
            if closed_count:
                logger.info("Closed {} inactive tickets", closed_count)
        except Exception:
            logger.exception("Inactive tickets sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
