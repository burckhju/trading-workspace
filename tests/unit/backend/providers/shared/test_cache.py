"""Tests for the process-local technical TTL cache."""

from datetime import UTC, datetime, timedelta

import pytest

from app.providers.shared.cache import InMemoryTtlCache
from tests.unit.backend.providers.shared.fakes import ManualClock


@pytest.mark.asyncio
async def test_cache_reports_miss_hit_and_rejected_stale_entry() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    cache = InMemoryTtlCache[str, int](clock=clock)

    assert (await cache.get("price")).hit is False
    await cache.set("price", 42, ttl=timedelta(seconds=10))

    hit = await cache.get("price")
    assert hit.value == 42
    assert hit.hit is True
    assert hit.stale is False

    clock.advance(10)
    stale = await cache.get("price")
    assert stale.value is None
    assert stale.hit is False
    assert stale.stale is True
    assert (await cache.get("price")).stale is False


@pytest.mark.asyncio
async def test_cache_delete_and_clear_are_explicit() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    cache = InMemoryTtlCache[str, int](clock=clock)
    await cache.set("a", 1, ttl=timedelta(minutes=1))
    await cache.set("b", 2, ttl=timedelta(minutes=1))

    assert await cache.delete("a") is True
    assert await cache.delete("a") is False
    await cache.clear()
    assert (await cache.get("b")).hit is False


@pytest.mark.asyncio
async def test_cache_rejects_non_positive_ttl() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    cache = InMemoryTtlCache[str, int](clock=clock)

    with pytest.raises(ValueError, match="ttl"):
        await cache.set("x", 1, ttl=timedelta(0))
