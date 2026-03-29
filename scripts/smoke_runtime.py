from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from urllib.error import URLError


def get_json(url: str, timeout: float = 10.0):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def post_json(url: str, payload: dict, timeout: float = 30.0):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def wait_for_health(url: str, timeout_s: float, interval_s: float) -> dict:
    deadline = time.time() + max(1.0, timeout_s)
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            health = get_json(url, timeout=max(1.0, min(5.0, interval_s)))
            if health.get("status") == "ok":
                return health
        except (URLError, TimeoutError, ConnectionResetError) as exc:
            last_exc = exc
        time.sleep(max(0.1, interval_s))

    if last_exc is not None:
        raise RuntimeError(f"health did not become ready before timeout: {last_exc}") from last_exc
    raise RuntimeError("health did not become ready before timeout")


def main() -> int:
    parser = argparse.ArgumentParser(description="Basic runtime smoke + latency checks")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--query", default="transformer")
    parser.add_argument("--health-timeout", type=float, default=10.0)
    parser.add_argument("--startup-wait", type=float, default=30.0)
    parser.add_argument("--health-interval", type=float, default=0.5)
    parser.add_argument("--search-timeout", type=float, default=90.0)
    parser.add_argument("--warmup", action="store_true", help="Run one warmup search before timed iterations")
    args = parser.parse_args()

    health_url = args.endpoint.rstrip("/") + "/health"
    search_url = args.endpoint.rstrip("/") + "/search"

    health = wait_for_health(
        health_url,
        timeout_s=max(args.health_timeout, args.startup_wait),
        interval_s=max(0.1, args.health_interval),
    )

    if args.warmup:
        post_json(
            search_url,
            {"query": args.query, "limit": args.limit},
            timeout=max(1.0, args.search_timeout),
        )

    latencies_ms: list[float] = []
    last_rows: list[dict] = []
    for _ in range(max(1, args.iterations)):
        t0 = time.perf_counter()
        rows = post_json(
            search_url,
            {"query": args.query, "limit": args.limit},
            timeout=max(1.0, args.search_timeout),
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        last_rows = rows

    p50 = statistics.median(latencies_ms)
    p95 = sorted(latencies_ms)[max(0, int(0.95 * len(latencies_ms)) - 1)]

    print(f"health={health.get('status')}")
    print(f"search_results={len(last_rows)}")
    print(f"latency_ms_p50={p50:.1f}")
    print(f"latency_ms_p95={p95:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
