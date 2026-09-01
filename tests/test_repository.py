import os

import asyncpg
import pytest

from bot.database import CustomerState, Repository
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


async def age_ticket(pool, user_id: int, days: int) -> None:
    await pool.execute(
        "UPDATE tickets SET last_activity_at = now() - make_interval(days => $2) WHERE user_id = $1", user_id, days
    )


async def test_migrations_are_idempotent(pool):
    await apply_migrations(pool)

    assert await pool.fetchval("SELECT count(*) FROM schema_migrations") == 3


async def test_unknown_customer_has_empty_state(repository):
    assert await repository.fetch_customer_state(1) == CustomerState(is_banned=False, topic_id=None)
    assert await repository.touch_open_ticket(1) is None


async def test_ticket_lifecycle(repository):
    await repository.bind_topic(1, 10)
    assert await repository.touch_open_ticket(1) == 10

    assert await repository.close_ticket_of_customer(1) == 10
    assert await repository.close_ticket_of_customer(1) is None
    assert await repository.touch_open_ticket(1) is None
    assert await repository.fetch_customer_state(1) == CustomerState(is_banned=False, topic_id=10)

    await repository.reopen_ticket(1)
    assert await repository.touch_open_ticket(1) == 10
    assert await repository.close_ticket_in_topic(10) == 1
    assert await repository.close_ticket_in_topic(10) is None
    assert await repository.touch_ticket_in_topic(10) == 1
    assert await repository.find_customer_in_topic(10) == 1


async def test_rebinding_replaces_deleted_topic(repository):
    await repository.bind_topic(1, 10)
    await repository.close_ticket_of_customer(1)

    await repository.bind_topic(1, 11)

    assert await repository.touch_open_ticket(1) == 11
    assert await repository.find_customer_in_topic(10) is None


async def test_ban_closes_ticket_and_blocks_fast_path(repository):
    await repository.bind_topic(1, 10)

    await repository.ban_customer(1)

    assert await repository.touch_open_ticket(1) is None
    assert await repository.fetch_customer_state(1) == CustomerState(is_banned=True, topic_id=10)
    assert await repository.unban_customer(1)
    assert not await repository.unban_customer(2)
    assert (await repository.fetch_customer_state(1)).is_banned is False


async def test_only_inactive_open_tickets_are_closed(pool, repository):
    for user_id in (1, 2, 3):
        await repository.bind_topic(user_id, user_id * 10)
    await age_ticket(pool, 1, 8)
    await age_ticket(pool, 2, 8)
    await repository.close_ticket_of_customer(2)

    assert await repository.close_inactive_tickets(7, 100) == [(1, 10)]
    assert await repository.close_inactive_tickets(7, 100) == []
    assert await repository.touch_open_ticket(3) == 30


async def test_recent_activity_keeps_old_ticket_open(pool, repository):
    await repository.bind_topic(1, 10)
    await age_ticket(pool, 1, 30)

    await repository.touch_ticket_in_topic(10)

    assert await repository.close_inactive_tickets(7, 100) == []
