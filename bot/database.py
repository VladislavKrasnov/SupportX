import asyncpg


class Repository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def register_customer(self, user_id: int) -> None:
        await self._pool.execute(
            "INSERT INTO customers (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
            user_id,
        )

    async def touch_open_ticket(self, user_id: int) -> int | None:
        return await self._pool.fetchval(
            """
            UPDATE tickets SET last_activity_at = now()
            WHERE user_id = $1 AND is_open
            RETURNING topic_id
            """,
            user_id,
        )

    async def find_topic_of_customer(self, user_id: int) -> int | None:
        return await self._pool.fetchval("SELECT topic_id FROM tickets WHERE user_id = $1", user_id)

    async def bind_topic(self, user_id: int, topic_id: int) -> None:
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.execute(
                "INSERT INTO customers (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
                user_id,
            )
            await connection.execute(
                """
                INSERT INTO tickets (user_id, topic_id) VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET topic_id = EXCLUDED.topic_id, is_open = TRUE, last_activity_at = now()
                """,
                user_id,
                topic_id,
            )

    async def reopen_ticket(self, user_id: int) -> None:
        await self._pool.execute(
            "UPDATE tickets SET is_open = TRUE, last_activity_at = now() WHERE user_id = $1",
            user_id,
        )

    async def close_ticket_of_customer(self, user_id: int) -> int | None:
        return await self._pool.fetchval(
            "UPDATE tickets SET is_open = FALSE WHERE user_id = $1 AND is_open RETURNING topic_id",
            user_id,
        )

    async def close_ticket_in_topic(self, topic_id: int) -> int | None:
        return await self._pool.fetchval(
            "UPDATE tickets SET is_open = FALSE WHERE topic_id = $1 AND is_open RETURNING user_id",
            topic_id,
        )

    async def touch_ticket_in_topic(self, topic_id: int) -> int | None:
        return await self._pool.fetchval(
            "UPDATE tickets SET last_activity_at = now() WHERE topic_id = $1 RETURNING user_id",
            topic_id,
        )
