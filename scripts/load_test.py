#!/usr/bin/env python3
"""WebMACS Sensor Scaling Load Test.

Stufentest: Fährt die Anzahl simulierter Sensoren stufenweise hoch und misst
Latenz, Throughput und Fehlerrate pro Stufe.

Usage:
    python3 scripts/load_test.py
    python3 scripts/load_test.py --stages 10,50,100 --duration 15
    python3 scripts/load_test.py --base-url http://192.168.1.50
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
import statistics
import sys
import time
from dataclasses import dataclass, field

import httpx

# ── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_STAGES = [10, 50, 100, 250, 500]
DEFAULT_DURATION = 30  # seconds per stage
DEFAULT_FREQUENCY = 2.0  # Hz — batches per second
DEFAULT_EMAIL = "admin@webmacs.io"
DEFAULT_PASSWORD = "admin123"

# ── ANSI colours ─────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"


# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class StageResult:
    """Metrics collected for a single load stage."""

    sensors: int
    duration: float
    total_batches: int = 0
    total_datapoints_sent: int = 0
    total_datapoints_accepted: int = 0
    errors: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    dashboard_latencies_ms: list[float] = field(default_factory=list)

    @property
    def throughput(self) -> float:
        return self.total_datapoints_accepted / self.duration if self.duration > 0 else 0

    @property
    def error_rate(self) -> float:
        return (self.errors / self.total_batches * 100) if self.total_batches > 0 else 0

    def percentile(self, data: list[float], p: int) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)

    def status_icon(self) -> str:
        p95 = self.percentile(self.latencies_ms, 95)
        if p95 > 1000 or self.error_rate > 2:
            return f"{RED}❌{RESET}"
        if p95 > 200 or self.error_rate > 0.5:
            return f"{YELLOW}⚠️{RESET}"
        return f"{GREEN}✅{RESET}"


# ── API Client ───────────────────────────────────────────────────────────────


class LoadTestClient:
    """Async HTTP client for WebMACS API."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.api = f"{self.base_url}/api/v1"
        self.email = email
        self.password = password
        self.token: str = ""
        # X-Forwarded-For: 127.0.0.1 makes the rate limiter treat us as trusted
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-Forwarded-For": "127.0.0.1"},
        )

    async def login(self) -> None:
        resp = await self.client.post(
            f"{self.api}/auth/login",
            json={"email": self.email, "password": self.password},
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"

    async def close(self) -> None:
        await self.client.aclose()

    # ── Events ──

    async def create_event(self, name: str, unit: str = "V", min_val: float = 0, max_val: float = 100) -> str:
        """Create an event and return its public_id."""
        resp = await self.client.post(
            f"{self.api}/events",
            json={
                "name": name,
                "min_value": min_val,
                "max_value": max_val,
                "unit": unit,
                "type": "sensor",
            },
        )
        resp.raise_for_status()
        # The create endpoint returns StatusResponse — get the event by listing
        resp2 = await self.client.get(f"{self.api}/events", params={"page_size": 100})
        resp2.raise_for_status()
        for ev in resp2.json()["data"]:
            if ev["name"] == name:
                return ev["public_id"]
        raise RuntimeError(f"Event '{name}' not found after creation")

    async def delete_event(self, public_id: str) -> None:
        await self.client.delete(f"{self.api}/events/{public_id}")

    async def list_events(self, page_size: int = 100) -> list[dict]:
        events = []
        page = 1
        while True:
            resp = await self.client.get(f"{self.api}/events", params={"page": page, "page_size": page_size})
            resp.raise_for_status()
            data = resp.json()
            events.extend(data["data"])
            if len(events) >= data["total"]:
                break
            page += 1
        return events

    # ── Plugins ──

    async def get_plugin_instance(self) -> dict | None:
        """Find the first enabled plugin instance."""
        resp = await self.client.get(f"{self.api}/plugins", params={"page_size": 100})
        resp.raise_for_status()
        data = resp.json()
        for inst in data.get("data", []):
            if inst.get("enabled"):
                return inst
        return None

    async def create_channel_mapping(
        self, plugin_public_id: str, channel_id: str, channel_name: str, event_public_id: str
    ) -> None:
        resp = await self.client.post(
            f"{self.api}/plugins/{plugin_public_id}/channels",
            json={
                "channel_id": channel_id,
                "channel_name": channel_name,
                "direction": "input",
                "unit": "V",
                "event_public_id": event_public_id,
            },
        )
        resp.raise_for_status()

    async def list_channel_mappings(self, plugin_public_id: str) -> list[dict]:
        resp = await self.client.get(f"{self.api}/plugins/{plugin_public_id}/channels")
        resp.raise_for_status()
        return resp.json()

    async def delete_channel_mapping(self, plugin_public_id: str, mapping_id: str) -> None:
        await self.client.delete(f"{self.api}/plugins/{plugin_public_id}/channels/{mapping_id}")

    # ── Datapoints ──

    async def send_batch(self, datapoints: list[dict]) -> httpx.Response:
        return await self.client.post(
            f"{self.api}/datapoints/batch",
            json={"datapoints": datapoints},
        )

    async def get_latest(self) -> httpx.Response:
        return await self.client.get(f"{self.api}/datapoints/latest")


# ── Test Setup & Teardown ────────────────────────────────────────────────────

LOAD_TEST_PREFIX = "__loadtest_"


async def setup_sensors(client: LoadTestClient, count: int) -> tuple[str, list[str]]:
    """Create N test sensors (events) linked to the current plugin instance.

    Returns (plugin_public_id, list_of_event_public_ids).
    """
    print(f"  {DIM}Setting up {count} test sensors...{RESET}", end="", flush=True)
    start = time.monotonic()

    # Find an enabled plugin instance
    plugin = await client.get_plugin_instance()
    if not plugin:
        print(f"\n{RED}ERROR: No enabled plugin instance found. Create one first.{RESET}")
        sys.exit(1)

    plugin_pid = plugin["public_id"]

    # Create events + channel mappings in parallel batches
    event_ids: list[str] = []
    batch_size = 50  # avoid overwhelming the backend
    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        tasks = []
        for i in range(batch_start, batch_end):
            name = f"{LOAD_TEST_PREFIX}sensor_{i:04d}"
            tasks.append(_create_sensor(client, plugin_pid, name, i))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                print(f"\n{RED}ERROR creating sensor: {r}{RESET}")
            else:
                event_ids.append(r)

    elapsed = time.monotonic() - start
    print(f" {GREEN}{len(event_ids)} sensors ready{RESET} ({elapsed:.1f}s)")
    return plugin_pid, event_ids


async def _create_sensor(client: LoadTestClient, plugin_pid: str, name: str, idx: int) -> str:
    """Create a single test sensor: Event + ChannelMapping."""
    # Create event
    resp = await client.client.post(
        f"{client.api}/events",
        json={
            "name": name,
            "min_value": 0,
            "max_value": 100,
            "unit": "V",
            "type": "sensor",
        },
    )
    if resp.status_code == 409:
        # Event already exists — find it
        pass
    else:
        resp.raise_for_status()

    # Find the event's public_id
    # Search by name in paginated results
    page = 1
    event_pid = None
    while event_pid is None:
        resp2 = await client.client.get(
            f"{client.api}/events",
            params={"page": page, "page_size": 100},
        )
        resp2.raise_for_status()
        data = resp2.json()
        for ev in data["data"]:
            if ev["name"] == name:
                event_pid = ev["public_id"]
                break
        if event_pid is None:
            if page * 100 >= data["total"]:
                raise RuntimeError(f"Event '{name}' not found")
            page += 1

    # Create channel mapping
    ch_id = f"loadtest_ch_{idx:04d}"
    try:
        await client.create_channel_mapping(plugin_pid, ch_id, name, event_pid)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 409:
            raise

    return event_pid


async def teardown_sensors(client: LoadTestClient, plugin_pid: str, event_ids: list[str]) -> None:
    """Remove all test sensors and their channel mappings."""
    print(f"  {DIM}Cleaning up {len(event_ids)} test sensors...{RESET}", end="", flush=True)
    start = time.monotonic()

    # Delete channel mappings
    mappings = await client.list_channel_mappings(plugin_pid)
    for m in mappings:
        if m.get("channel_id", "").startswith("loadtest_ch_"):
            try:
                await client.delete_channel_mapping(plugin_pid, m["public_id"])
            except Exception:
                pass

    # Delete events
    batch_size = 50
    for i in range(0, len(event_ids), batch_size):
        batch = event_ids[i : i + batch_size]
        tasks = [client.delete_event(eid) for eid in batch]
        await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.monotonic() - start
    print(f" {GREEN}done{RESET} ({elapsed:.1f}s)")


# ── Load Generation ─────────────────────────────────────────────────────────


async def run_stage(
    client: LoadTestClient,
    event_ids: list[str],
    duration: float,
    frequency: float,
) -> StageResult:
    """Run a single load stage: send batches for `duration` seconds at `frequency` Hz."""
    result = StageResult(sensors=len(event_ids), duration=duration)
    interval = 1.0 / frequency
    end_time = time.monotonic() + duration

    while time.monotonic() < end_time:
        tick_start = time.monotonic()

        # Build batch: one reading per sensor (like the real controller)
        batch = [
            {"value": round(random.uniform(10, 90), 2), "event_public_id": eid}
            for eid in event_ids
        ]

        # Send batch
        try:
            t0 = time.monotonic()
            resp = await client.send_batch(batch)
            latency_ms = (time.monotonic() - t0) * 1000

            result.total_batches += 1
            result.total_datapoints_sent += len(batch)
            result.latencies_ms.append(latency_ms)

            if resp.status_code == 201:
                # Parse accepted count from message
                msg = resp.json().get("message", "")
                try:
                    accepted = int(msg.split()[0])
                except (ValueError, IndexError):
                    accepted = len(batch)
                result.total_datapoints_accepted += accepted
            else:
                result.errors += 1
        except Exception:
            result.errors += 1
            result.total_batches += 1

        # Simulate dashboard poll every 2 seconds
        if result.total_batches % max(1, int(frequency * 2)) == 0:
            try:
                t0 = time.monotonic()
                await client.get_latest()
                dash_ms = (time.monotonic() - t0) * 1000
                result.dashboard_latencies_ms.append(dash_ms)
            except Exception:
                pass

        # Sleep remaining interval
        elapsed = time.monotonic() - tick_start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

    return result


# ── Output ───────────────────────────────────────────────────────────────────


def print_header() -> None:
    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║                          WebMACS Sensor Scaling Load Test                              ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")
    print()


def print_stage_header(stage_num: int, sensors: int, duration: float, frequency: float) -> None:
    dp_per_sec = sensors * frequency
    print()
    print(f"{BOLD}── Stage {stage_num}: {sensors} sensors @ {frequency} Hz = {dp_per_sec:.0f} dp/s for {duration:.0f}s ──{RESET}")


def print_stage_result(r: StageResult) -> None:
    p50 = r.percentile(r.latencies_ms, 50)
    p95 = r.percentile(r.latencies_ms, 95)
    p99 = r.percentile(r.latencies_ms, 99)
    dash_p95 = r.percentile(r.dashboard_latencies_ms, 95) if r.dashboard_latencies_ms else 0

    icon = r.status_icon()

    print(f"  {icon}  Throughput:  {r.throughput:>8.1f} dp/s  (sent {r.total_datapoints_sent}, accepted {r.total_datapoints_accepted})")
    print(f"      Batch P50: {p50:>8.1f} ms   P95: {p95:>8.1f} ms   P99: {p99:>8.1f} ms")
    if r.dashboard_latencies_ms:
        print(f"      Dashboard P95: {dash_p95:>6.1f} ms  (GET /datapoints/latest)")
    print(f"      Errors:    {r.errors}/{r.total_batches} ({r.error_rate:.1f}%)")


def print_summary(results: list[StageResult]) -> None:
    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║                                    SUMMARY                                             ║{RESET}")
    print(f"{BOLD}{CYAN}╠══════════╦══════════╦══════════╦══════════╦══════════╦══════════╦════════╦═══════════════╣{RESET}")
    print(f"{BOLD}{CYAN}║ Sensors  ║ dp/s     ║ P50 ms   ║ P95 ms   ║ P99 ms   ║ Dash P95 ║ Errors ║ Status        ║{RESET}")
    print(f"{BOLD}{CYAN}╠══════════╬══════════╬══════════╬══════════╬══════════╬══════════╬════════╬═══════════════╣{RESET}")

    for r in results:
        p50 = r.percentile(r.latencies_ms, 50)
        p95 = r.percentile(r.latencies_ms, 95)
        p99 = r.percentile(r.latencies_ms, 99)
        dash = r.percentile(r.dashboard_latencies_ms, 95) if r.dashboard_latencies_ms else 0
        icon = r.status_icon()

        print(
            f"{CYAN}║{RESET} {r.sensors:>7}  "
            f"{CYAN}║{RESET} {r.throughput:>7.0f}  "
            f"{CYAN}║{RESET} {p50:>7.1f}  "
            f"{CYAN}║{RESET} {p95:>7.1f}  "
            f"{CYAN}║{RESET} {p99:>7.1f}  "
            f"{CYAN}║{RESET} {dash:>7.1f}  "
            f"{CYAN}║{RESET} {r.error_rate:>4.1f}%  "
            f"{CYAN}║{RESET} {icon}            {CYAN}║{RESET}"
        )

    print(f"{BOLD}{CYAN}╚══════════╩══════════╩══════════╩══════════╩══════════╩══════════╩════════╩═══════════════╝{RESET}")

    # Find the sweet spot
    best = None
    for r in results:
        p95 = r.percentile(r.latencies_ms, 95)
        if p95 < 200 and r.error_rate == 0:
            best = r
    if best:
        print(f"\n  {GREEN}Sweet spot: {best.sensors} sensors @ {best.throughput:.0f} dp/s with P95 < 200ms{RESET}")
    else:
        print(f"\n  {YELLOW}Even {results[0].sensors} sensors showed degradation — consider tuning.{RESET}")

    # Find the breaking point
    broken = None
    for r in results:
        p95 = r.percentile(r.latencies_ms, 95)
        if p95 > 1000 or r.error_rate > 2:
            broken = r
            break
    if broken:
        print(f"  {RED}Breaking point: {broken.sensors} sensors (P95={r.percentile(broken.latencies_ms, 95):.0f}ms, {broken.error_rate:.1f}% errors){RESET}")
    else:
        print(f"  {GREEN}No breaking point found — system handled all stages!{RESET}")


# ── Main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    parser = argparse.ArgumentParser(description="WebMACS Sensor Scaling Load Test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL")
    parser.add_argument("--stages", default=",".join(str(s) for s in DEFAULT_STAGES), help="Comma-separated sensor counts")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Seconds per stage")
    parser.add_argument("--frequency", type=float, default=DEFAULT_FREQUENCY, help="Batches per second")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    stages = [int(s.strip()) for s in args.stages.split(",")]

    print_header()
    print(f"  Target:    {args.base_url}")
    print(f"  Stages:    {stages}")
    print(f"  Duration:  {args.duration}s per stage")
    print(f"  Frequency: {args.frequency} Hz")
    print()

    client = LoadTestClient(args.base_url, args.email, args.password)

    try:
        # Authenticate
        print(f"  {DIM}Authenticating...{RESET}", end="", flush=True)
        await client.login()
        print(f" {GREEN}OK{RESET}")

        results: list[StageResult] = []

        for stage_idx, sensor_count in enumerate(stages, 1):
            print_stage_header(stage_idx, sensor_count, args.duration, args.frequency)

            # Setup
            plugin_pid, event_ids = await setup_sensors(client, sensor_count)

            if not event_ids:
                print(f"  {RED}No sensors created — skipping stage{RESET}")
                continue

            # Warm-up: 2 seconds
            print(f"  {DIM}Warm-up (2s)...{RESET}", end="", flush=True)
            await asyncio.sleep(0.5)
            # Send a few warm-up batches
            for _ in range(3):
                batch = [{"value": 42.0, "event_public_id": eid} for eid in event_ids[:10]]
                await client.send_batch(batch)
                await asyncio.sleep(0.3)
            print(f" {GREEN}OK{RESET}")

            # Run
            print(f"  {BOLD}Running...{RESET} ", end="", flush=True)
            stage_start = time.monotonic()
            result = await run_stage(client, event_ids, args.duration, args.frequency)
            stage_elapsed = time.monotonic() - stage_start
            result.duration = stage_elapsed
            print(f"{GREEN}done{RESET} ({stage_elapsed:.1f}s)")

            print_stage_result(result)
            results.append(result)

            # Teardown
            await teardown_sensors(client, plugin_pid, event_ids)

            # Brief pause between stages
            if stage_idx < len(stages):
                print(f"  {DIM}Cooldown (3s)...{RESET}")
                await asyncio.sleep(3)

        # Summary
        if results:
            print_summary(results)

    except httpx.HTTPStatusError as e:
        print(f"\n{RED}HTTP Error: {e.response.status_code} — {e.response.text}{RESET}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
    finally:
        await client.close()

    print()


if __name__ == "__main__":
    asyncio.run(main())
