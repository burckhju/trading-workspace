from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.features.notification.domain.models import (
    DeliveryPreparation,
    DeliveryResult,
    DeliveryStatus,
)
from app.features.notification.service.delivery import NotificationDeliveryAdapter

PendingNotificationCursor = tuple[datetime, UUID]


class DurableNotificationDeliveryStore(Protocol):
    async def list_pending_notification_ids(self, *, limit: int) -> tuple[UUID, ...]: ...

    async def list_pending_notification_page(
        self,
        *,
        limit: int,
        created_before: datetime,
        after: PendingNotificationCursor | None = None,
    ) -> tuple[PendingNotificationCursor, ...]: ...

    async def prepare(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        now: datetime,
        stale_before: datetime,
        max_attempts: int,
    ) -> DeliveryPreparation: ...

    async def complete(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        result: DeliveryResult,
        completed_at: datetime,
        max_attempts: int,
    ) -> None: ...


class DurableNotificationDeliveryService:
    """Deliver only after the in-progress attempt has been durably committed."""

    def __init__(
        self,
        *,
        store: DurableNotificationDeliveryStore,
        adapter: NotificationDeliveryAdapter,
        new_id: Callable[[], UUID],
        now: Callable[[], datetime],
        max_attempts: int = 3,
        in_progress_timeout: timedelta = timedelta(minutes=5),
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if in_progress_timeout <= timedelta(0):
            raise ValueError("in_progress_timeout must be positive")
        self._store = store
        self._adapter = adapter
        self._new_id = new_id
        self._now = now
        self._max_attempts = max_attempts
        self._in_progress_timeout = in_progress_timeout

    async def deliver_pending(self, *, limit: int = 100) -> tuple[DeliveryResult, ...]:
        """Use a fixed cycle cutoff and at most ``limit`` external adapter calls.

        Paused or already terminal preparations do not consume the send budget.
        Keyset pages advance past them exactly once in this cycle, including when
        other workers finish rows. Records dated at/after the initial cutoff
        wait for the next cycle; the cutoff is not a business validity period.
        Results include non-send decisions and can therefore exceed ``limit``.
        """
        if limit < 1:
            raise ValueError("limit must be positive")
        cutoff = self._now()
        if cutoff.utcoffset() is None:
            raise ValueError("delivery cycle requires an aware cutoff")
        after: PendingNotificationCursor | None = None
        results: list[DeliveryResult] = []
        sends = 0
        while sends < limit:
            page = await self._store.list_pending_notification_page(
                limit=100, created_before=cutoff, after=after
            )
            if not page:
                break
            for key in page:
                if after is not None and key <= after:
                    raise RuntimeError("pending notification page did not advance")
                result, sent = await self._deliver(key[1])
                results.append(result)
                sends += int(sent)
                after = key
                if sends == limit:
                    return tuple(results)
        return tuple(results)

    async def deliver(self, notification_id: UUID) -> DeliveryResult:
        result, _ = await self._deliver(notification_id)
        return result

    async def _deliver(self, notification_id: UUID) -> tuple[DeliveryResult, bool]:
        """Report actual adapter use without interpreting provider error strings."""
        started_at = self._now()
        preparation = await self._store.prepare(
            notification_id=notification_id,
            attempt_id=self._new_id(),
            now=started_at,
            stale_before=started_at - self._in_progress_timeout,
            max_attempts=self._max_attempts,
        )
        if preparation.terminal_result is not None:
            return preparation.terminal_result, False
        if preparation.attempt is None:
            raise RuntimeError("delivery preparation produced neither attempt nor terminal result")

        try:
            result = await self._adapter.deliver(body=preparation.notification.body)
        except Exception as error:
            result = DeliveryResult(
                status=DeliveryStatus.FAILED,
                retryable=True,
                error_code="DELIVERY_EXCEPTION",
                error_message=str(error)[:1000],
            )

        await self._store.complete(
            notification_id=notification_id,
            attempt_id=preparation.attempt.id,
            result=result,
            completed_at=self._now(),
            max_attempts=self._max_attempts,
        )
        return result, True
