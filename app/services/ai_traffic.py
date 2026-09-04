"""Bounded, tenant-aware admission control for AI traffic."""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
import threading
import time
import weakref

from fastapi import HTTPException

from app.core.config import (
    AI_GATEWAY_CUSTOMER_CONCURRENCY,
    AI_GATEWAY_CUSTOMER_QUEUE_LIMIT,
    AI_GATEWAY_GLOBAL_CONCURRENCY,
    AI_GATEWAY_QUEUE_LIMIT,
    AI_GATEWAY_QUEUE_TIMEOUT_SECONDS,
)


class TrafficManager:
    def __init__(self):
        self.global_limit = AI_GATEWAY_GLOBAL_CONCURRENCY
        self.customer_limit = AI_GATEWAY_CUSTOMER_CONCURRENCY
        self.queue_limit = AI_GATEWAY_QUEUE_LIMIT
        self.customer_queue_limit = AI_GATEWAY_CUSTOMER_QUEUE_LIMIT
        self.timeout = AI_GATEWAY_QUEUE_TIMEOUT_SECONDS
        self._global = asyncio.Semaphore(self.global_limit)
        self._customers: dict[int, asyncio.Semaphore] = {}
        self._counter_lock = threading.Lock()
        self._queued = 0
        self._queued_by_customer = defaultdict(int)

    def snapshot(self) -> dict:
        with self._counter_lock:
            return {"queue_size": self._queued, "queued_customers": len(self._queued_by_customer)}

    @asynccontextmanager
    async def slot(self, company_id: int):
        with self._counter_lock:
            if self._queued >= self.queue_limit:
                raise HTTPException(status_code=503, detail="AI request queue is full. Please try again shortly.")
            if self._queued_by_customer[company_id] >= self.customer_queue_limit:
                raise HTTPException(status_code=429, detail="Too many queued AI requests for this customer.")
            self._queued += 1
            self._queued_by_customer[company_id] += 1
        customer = self._customers.setdefault(company_id, asyncio.Semaphore(self.customer_limit))
        customer_acquired = global_acquired = False
        started = time.monotonic()
        try:
            await asyncio.wait_for(customer.acquire(), timeout=self.timeout)
            customer_acquired = True
            remaining = max(0.001, self.timeout - (time.monotonic() - started))
            await asyncio.wait_for(self._global.acquire(), timeout=remaining)
            global_acquired = True
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=503, detail="AI request queue wait timed out. Please retry.") from exc
        finally:
            with self._counter_lock:
                self._queued -= 1
                self._queued_by_customer[company_id] -= 1
                if self._queued_by_customer[company_id] == 0:
                    del self._queued_by_customer[company_id]
            if not global_acquired and customer_acquired:
                customer.release()
        try:
            yield
        finally:
            self._global.release()
            customer.release()


_managers = weakref.WeakKeyDictionary()
_managers_lock = threading.Lock()


def get_traffic_manager() -> TrafficManager:
    loop = asyncio.get_running_loop()
    with _managers_lock:
        manager = _managers.get(loop)
        if manager is None:
            manager = TrafficManager()
            _managers[loop] = manager
        return manager
