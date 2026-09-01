from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True, slots=True)
class CustomerState:
    is_banned: bool
    topic_id: int | None


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
            UPDATE tickets AS ticket
            SET last_activity_at = now()
            FROM customers AS customer
            WHERE ticket.user_id = $1
              AND ticket.is_open
              AND customer.user_id = ticket.user_id
              AND NOT customer.is_banned
            RETURNING ticket.topic_id
            """,
            user_id,
        )

    async def fetch_customer_state(self, user_id: int) -> CustomerState:
        row = await self._pool.fetchrow(
            """
            SELECT customer.is_banned, ticket.topic_id
            FROM customers AS customer
            LEFT JOIN tickets AS ticket USING (user_id)
            WHERE customer.user_id = $1
            """,
            user_id,
        )
        if row is None:
            return CustomerState(is_banned=False, topic_id=None)
        return CustomerState(is_banned=row["is_banned"], topic_id=row["topic_id"])

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

    async def find_customer_in_topic(self, topic_id: int) -> int | None:
        return await self._pool.fetchval("SELECT user_id FROM tickets WHERE topic_id = $1", topic_id)

    async def ban_customer(self, user_id: int) -> None:
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.execute("UPDATE customers SET is_banned = TRUE WHERE user_id = $1", user_id)
            await connection.execute("UPDATE tickets SET is_open = FALSE WHERE user_id = $1", user_id)

    async def unban_customer(self, user_id: int) -> bool:
        unbanned_user_id = await self._pool.fetchval(
            "UPDATE customers SET is_banned = FALSE WHERE user_id = $1 RETURNING user_id",
            user_id,
        )
        return unbanned_user_id is not None

    async def close_inactive_tickets(self, inactive_days: int, batch_size: int) -> list[tuple[int, int]]:
        rows = await self._pool.fetch(
            """
            UPDATE tickets SET is_open = FALSE
            WHERE user_id IN (
                SELECT user_id FROM tickets
                WHERE is_open AND last_activity_at < now() - make_interval(days => $1)
                ORDER BY last_activity_at
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            )
            RETURNING user_id, topic_id
            """,
            inactive_days,
            batch_size,
        )
        return [(row["user_id"], row["topic_id"]) for row in rows]
