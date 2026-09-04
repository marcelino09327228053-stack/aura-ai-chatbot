"""Dependency-free synthetic load test for AI Gateway admission controls."""

import argparse
import asyncio
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.services.ai_traffic import TrafficManager


async def run_load(requests: int, customers: int, service_ms: float,
                   global_limit: int, customer_limit: int) -> dict:
    manager = TrafficManager()
    manager.global_limit = global_limit
    manager.customer_limit = customer_limit
    manager.queue_limit = max(manager.queue_limit, requests + 1)
    manager.customer_queue_limit = max(manager.customer_queue_limit, requests + 1)
    manager._global = asyncio.Semaphore(global_limit)
    manager._customers = {}
    active = max_active = 0
    active_by_customer = {}
    max_by_customer = {}
    latencies = []
    rejected = 0
    lock = asyncio.Lock()

    async def one(index: int):
        nonlocal active, max_active, rejected
        company_id = index % customers + 1
        started = time.perf_counter()
        try:
            async with manager.slot(company_id):
                async with lock:
                    active += 1
                    active_by_customer[company_id] = active_by_customer.get(company_id, 0) + 1
                    max_active = max(max_active, active)
                    max_by_customer[company_id] = max(
                        max_by_customer.get(company_id, 0), active_by_customer[company_id]
                    )
                await asyncio.sleep(service_ms / 1000)
                async with lock:
                    active -= 1
                    active_by_customer[company_id] -= 1
        except HTTPException:
            rejected += 1
        finally:
            latencies.append((time.perf_counter() - started) * 1000)

    wall_started = time.perf_counter()
    await asyncio.gather(*(one(index) for index in range(requests)))
    ordered = sorted(latencies)
    percentile = lambda pct: ordered[min(len(ordered) - 1, int(len(ordered) * pct))]
    return {
        "requests": requests,
        "customers": customers,
        "rejected": rejected,
        "max_global_concurrency": max_active,
        "max_customer_concurrency": max(max_by_customer.values(), default=0),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(percentile(0.50), 2),
            "p95": round(percentile(0.95), 2),
            "max": round(max(latencies), 2),
        },
        "wall_time_ms": round((time.perf_counter() - wall_started) * 1000, 2),
        "limits_respected": max_active <= global_limit and
                            max(max_by_customer.values(), default=0) <= customer_limit,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--customers", type=int, default=20)
    parser.add_argument("--service-ms", type=float, default=25)
    parser.add_argument("--global-limit", type=int, default=20)
    parser.add_argument("--customer-limit", type=int, default=2)
    args = parser.parse_args()
    result = asyncio.run(run_load(args.requests, args.customers, args.service_ms,
                                  args.global_limit, args.customer_limit))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["limits_respected"] and not result["rejected"] else 1)


if __name__ == "__main__":
    main()
