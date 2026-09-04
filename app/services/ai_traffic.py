"""Bounded, tenant-aware admission control for AI traffic."""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
import threading
import time
import weakref
import uuid

from fastapi import HTTPException

from app.core.config import (
    AI_GATEWAY_CUSTOMER_CONCURRENCY,
    AI_GATEWAY_CUSTOMER_QUEUE_LIMIT,
    AI_GATEWAY_GLOBAL_CONCURRENCY,
    AI_GATEWAY_QUEUE_LIMIT,
    AI_GATEWAY_QUEUE_TIMEOUT_SECONDS,
    AI_GATEWAY_DISTRIBUTED_LEASE_SECONDS,
    AI_GATEWAY_QUEUE_POLL_SECONDS,
)
from app.infrastructure.redis.client import get_client


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


class RedisTrafficManager:
    """Cross-worker bounded admission using expiring Redis semaphore leases."""

    _ADMIT = """
    local total = tonumber(redis.call('GET', KEYS[1]) or '0')
    local customer = tonumber(redis.call('GET', KEYS[2]) or '0')
    if total >= tonumber(ARGV[1]) then return 1 end
    if customer >= tonumber(ARGV[2]) then return 2 end
    redis.call('INCR', KEYS[1]); redis.call('EXPIRE', KEYS[1], ARGV[3])
    redis.call('INCR', KEYS[2]); redis.call('EXPIRE', KEYS[2], ARGV[3])
    return 0
    """
    _ACQUIRE = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
    redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', ARGV[1])
    if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
    if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then return 0 end
    redis.call('ZADD', KEYS[1], ARGV[4], ARGV[5])
    redis.call('ZADD', KEYS[2], ARGV[4], ARGV[5])
    redis.call('EXPIRE', KEYS[1], ARGV[6]); redis.call('EXPIRE', KEYS[2], ARGV[6])
    return 1
    """

    def __init__(self, client):
        self.client = client
        self.global_limit = AI_GATEWAY_GLOBAL_CONCURRENCY
        self.customer_limit = AI_GATEWAY_CUSTOMER_CONCURRENCY
        self.queue_limit = AI_GATEWAY_QUEUE_LIMIT
        self.customer_queue_limit = AI_GATEWAY_CUSTOMER_QUEUE_LIMIT
        self.timeout = AI_GATEWAY_QUEUE_TIMEOUT_SECONDS
        self.lease_seconds = AI_GATEWAY_DISTRIBUTED_LEASE_SECONDS

    async def _call(self, function, *args):
        return await asyncio.to_thread(function, *args)

    async def _dequeue(self, company_id: int):
        pipe = self.client.pipeline()
        pipe.decr("aura:ai:queue:total").decr(f"aura:ai:queue:customer:{company_id}")
        await self._call(pipe.execute)

    def snapshot(self) -> dict:
        try:
            total = int(self.client.get("aura:ai:queue:total") or 0)
        except Exception:
            total = 0
        return {"queue_size": max(0, total), "distributed": True}

    @asynccontextmanager
    async def slot(self, company_id: int):
        customer_queue = f"aura:ai:queue:customer:{company_id}"
        admitted = await self._call(
            self.client.eval, self._ADMIT, 2, "aura:ai:queue:total", customer_queue,
            self.queue_limit, self.customer_queue_limit,
            max(self.lease_seconds, int(self.timeout) + 5),
        )
        if admitted == 1:
            raise HTTPException(status_code=503, detail="AI request queue is full. Please try again shortly.")
        if admitted == 2:
            raise HTTPException(status_code=429, detail="Too many queued AI requests for this customer.")
        lease_id = str(uuid.uuid4())
        global_key = "aura:ai:active:global"
        customer_key = f"aura:ai:active:customer:{company_id}"
        started = time.monotonic()
        acquired = False
        try:
            while time.monotonic() - started < self.timeout:
                now = time.time()
                acquired = bool(await self._call(
                    self.client.eval, self._ACQUIRE, 2, global_key, customer_key,
                    now, self.global_limit, self.customer_limit,
                    now + self.lease_seconds, lease_id, self.lease_seconds,
                ))
                if acquired: break
                await asyncio.sleep(AI_GATEWAY_QUEUE_POLL_SECONDS)
            if not acquired:
                raise HTTPException(status_code=503, detail="AI request queue wait timed out. Please retry.")
        finally:
            await self._dequeue(company_id)
        try:
            yield
        finally:
            await self._call(self.client.zrem, global_key, lease_id)
            await self._call(self.client.zrem, customer_key, lease_id)


_managers = weakref.WeakKeyDictionary()
_managers_lock = threading.Lock()


def get_traffic_manager() -> TrafficManager:
    loop = asyncio.get_running_loop()
    client = get_client()
    if client is not None:
        with _managers_lock:
            manager = _managers.get(loop)
            if manager is None or not isinstance(manager, RedisTrafficManager):
                manager = RedisTrafficManager(client)
                _managers[loop] = manager
            return manager
    with _managers_lock:
        manager = _managers.get(loop)
        if manager is None:
            manager = TrafficManager()
            _managers[loop] = manager
        return manager
