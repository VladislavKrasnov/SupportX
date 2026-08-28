from pathlib import Path

import asyncpg
from loguru import logger

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent.parent / "migrations"
MIGRATIONS_ADVISORY_LOCK_KEY = 7_264_119_053


async def apply_migrations(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as connection, connection.transaction():
        await connection.execute("SELECT pg_advisory_xact_lock($1)", MIGRATIONS_ADVISORY_LOCK_KEY)
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied_names = {row["name"] for row in await connection.fetch("SELECT name FROM schema_migrations")}
        for migration_path in sorted(MIGRATIONS_DIRECTORY.glob("*.sql")):
            if migration_path.name in applied_names:
                continue
            await connection.execute(migration_path.read_text(encoding="utf-8"))
            await connection.execute("INSERT INTO schema_migrations (name) VALUES ($1)", migration_path.name)
            logger.info("Applied migration {}", migration_path.name)
