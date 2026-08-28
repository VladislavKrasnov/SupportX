import os

import asyncpg
import pytest

from bot.database import Repository
from bot.schema import apply_migrations

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")


@pytest.fixture
async def pool():
    pool = await asyncpg.create_pool(TEST_DATABASE_URL)
    await pool.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await apply_migrations(pool)
    yield pool
    await pool.close()


@pytest.fixture
def repository(pool) -> Repository:
    return Repository(pool)


async def test_migrations_are_idempotent(pool):
    await apply_migrations(pool)

    assert await pool.fetchval("SELECT count(*) FROM schema_migrations") == 1


async def test_unknown_customer_has_empty_state(repository):
    assert await repository.find_topic_of_customer(1) is None
    assert await repository.touch_open_ticket(1) is None


async def test_ticket_lifecycle(repository):
    await repository.bind_topic(1, 10)
    assert await repository.touch_open_ticket(1) == 10

    assert await repository.close_ticket_of_customer(1) == 10
    assert await repository.close_ticket_of_customer(1) is None
    assert await repository.touch_open_ticket(1) is None
    assert await repository.find_topic_of_customer(1) == 10

    await repository.reopen_ticket(1)
    assert await repository.touch_open_ticket(1) == 10
    assert await repository.close_ticket_in_topic(10) == 1
    assert await repository.close_ticket_in_topic(10) is None
    assert await repository.touch_ticket_in_topic(10) == 1


async def test_rebinding_replaces_deleted_topic(repository):
    await repository.bind_topic(1, 10)
    await repository.close_ticket_of_customer(1)

    await repository.bind_topic(1, 11)

    assert await repository.touch_open_ticket(1) == 11
    assert await repository.touch_ticket_in_topic(10) is None
