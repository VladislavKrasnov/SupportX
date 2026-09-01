import asyncpg
from typing import Optional, List, Tuple

class DatabaseClient:
    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if not self._pool:
            self._pool = await asyncpg.create_pool(self._database_url)
            
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()

    async def register_user(self, user_id: int) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING", 
                user_id
            )

    async def link_topic_to_user(self, user_id: int, topic_id: int) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO topics (user_id, topic_id) VALUES ($1, $2)", 
                user_id, topic_id
            )

    async def retrieve_topic_for_user(self, user_id: int) -> Optional[int]:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT topic_id FROM topics WHERE user_id = $1", 
                user_id
            )
            return row["topic_id"] if row else None

    async def retrieve_user_for_topic(self, topic_id: int) -> Optional[int]:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT user_id FROM topics WHERE topic_id = $1", 
                topic_id
            )
            return row["user_id"] if row else None

    async def remove_topic_link(self, user_id: int) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM topics WHERE user_id = $1", 
                user_id
            )

    async def ban_user(self, user_id: int) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                "UPDATE users SET is_banned = TRUE WHERE user_id = $1",
                user_id
            )

    async def is_user_banned(self, user_id: int) -> bool:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT is_banned FROM users WHERE user_id = $1",
                user_id
            )
            return row["is_banned"] if row and row["is_banned"] is not None else False

    async def unban_user(self, user_id: int) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                "UPDATE users SET is_banned = FALSE WHERE user_id = $1",
                user_id
            )

    async def get_expired_topics(self, days: int) -> List[Tuple[int, int]]:
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT user_id, topic_id FROM topics WHERE created_at < CURRENT_TIMESTAMP - ($1 || ' days')::INTERVAL",
                str(days)
            )
            return [(row["user_id"], row["topic_id"]) for row in rows]
