from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ChapterRunResult:
    chapter_idx: int
    generate_status_code: int
    generate_ok: bool
    job_id: str | None
    terminal_status: str | None
    terminal_progress: int | None
    output_url: str | None
    error: str | None
    elapsed_seconds: float | None


@dataclass(frozen=True)
class ConflictProbeResult:
    attempted: bool
    first_status_code: int | None
    second_status_code: int | None
    second_detail: str | None
    passed: bool


def _parse_chapter_indices(raw: str) -> list[int]:
    values: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_raw, end_raw = token.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)
            values.extend(list(range(start, end + 1)))
        else:
            values.append(int(token))
    # preserve order while de-duplicating
    seen: set[int] = set()
    ordered: list[int] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _poll_job(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    job_id: str,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    while True:
        response = await client.get(
            f"{base_url}/jobs/{job_id}",
            headers=_headers(token),
            timeout=30.0,
        )
        payload = response.json()
        status = payload.get("status")
        if status in {"completed", "failed"}:
            elapsed = time.perf_counter() - started
            payload["elapsed_seconds"] = round(elapsed, 2)
            return payload

        elapsed = time.perf_counter() - started
        if elapsed > timeout_seconds:
            payload["status"] = "timeout"
            payload["error"] = f"Polling timeout after {timeout_seconds}s"
            payload["elapsed_seconds"] = round(elapsed, 2)
            return payload
        await asyncio.sleep(poll_interval_seconds)


async def _run_single_chapter(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    book_id: str,
    chapter_idx: int,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> ChapterRunResult:
    generate_response = await client.post(
        f"{base_url}/books/{book_id}/chapters/{chapter_idx}/generate",
        headers=_headers(token),
        timeout=30.0,
    )
    generate_payload = generate_response.json()
    if generate_response.status_code != 202:
        return ChapterRunResult(
            chapter_idx=chapter_idx,
            generate_status_code=generate_response.status_code,
            generate_ok=False,
            job_id=None,
            terminal_status=None,
            terminal_progress=None,
            output_url=None,
            error=str(generate_payload.get("detail")),
            elapsed_seconds=None,
        )

    job_id = generate_payload.get("job_id")
    if not isinstance(job_id, str):
        return ChapterRunResult(
            chapter_idx=chapter_idx,
            generate_status_code=generate_response.status_code,
            generate_ok=False,
            job_id=None,
            terminal_status=None,
            terminal_progress=None,
            output_url=None,
            error="Missing job_id in generate response",
            elapsed_seconds=None,
        )

    terminal = await _poll_job(
        client=client,
        base_url=base_url,
        token=token,
        job_id=job_id,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )

    return ChapterRunResult(
        chapter_idx=chapter_idx,
        generate_status_code=generate_response.status_code,
        generate_ok=True,
        job_id=job_id,
        terminal_status=str(terminal.get("status")),
        terminal_progress=int(terminal.get("progress", 0)),
        output_url=terminal.get("output_url"),
        error=terminal.get("error"),
        elapsed_seconds=float(terminal.get("elapsed_seconds", 0.0)),
    )


async def _probe_conflict_behavior(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    book_id: str,
    chapter_idx: int,
) -> ConflictProbeResult:
    first = await client.post(
        f"{base_url}/books/{book_id}/chapters/{chapter_idx}/generate",
        headers=_headers(token),
        timeout=30.0,
    )
    second = await client.post(
        f"{base_url}/books/{book_id}/chapters/{chapter_idx}/generate",
        headers=_headers(token),
        timeout=30.0,
    )
    second_detail: str | None = None
    try:
        second_detail = second.json().get("detail")
    except Exception:  # noqa: BLE001
        second_detail = None
    return ConflictProbeResult(
        attempted=True,
        first_status_code=first.status_code,
        second_status_code=second.status_code,
        second_detail=second_detail,
        passed=(first.status_code == 202 and second.status_code == 409),
    )


async def _run(args: argparse.Namespace) -> int:
    chapter_indices = _parse_chapter_indices(args.chapters)
    if not chapter_indices:
        raise ValueError("No chapter indices were parsed from --chapters")

    timeout_seconds = int(args.timeout_seconds)
    poll_interval = float(args.poll_interval_seconds)
    base_url = args.base_url.rstrip("/")

    async with httpx.AsyncClient() as client:
        chapter_results: list[ChapterRunResult] = []
        for chapter_idx in chapter_indices:
            chapter_results.append(
                await _run_single_chapter(
                    client=client,
                    base_url=base_url,
                    token=args.bearer_token,
                    book_id=args.book_id,
                    chapter_idx=chapter_idx,
                    timeout_seconds=timeout_seconds,
                    poll_interval_seconds=poll_interval,
                )
            )

        conflict = None
        if args.check_conflict:
            conflict = await _probe_conflict_behavior(
                client=client,
                base_url=base_url,
                token=args.bearer_token,
                book_id=args.book_id,
                chapter_idx=chapter_indices[0],
            )

    completed = [item for item in chapter_results if item.terminal_status == "completed"]
    failed = [item for item in chapter_results if item.terminal_status == "failed"]
    timeout = [item for item in chapter_results if item.terminal_status == "timeout"]
    report = {
        "book_id": args.book_id,
        "chapters": chapter_indices,
        "summary": {
            "total": len(chapter_results),
            "completed": len(completed),
            "failed": len(failed),
            "timeout": len(timeout),
        },
        "results": [asdict(item) for item in chapter_results],
        "conflict_probe": asdict(conflict) if conflict else None,
    }
    print(json.dumps(report, indent=2))
    return 0 if not failed and not timeout else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime Phase 4 validation runner")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="Backend API base URL")
    parser.add_argument("--book-id", required=True, help="Book UUID to validate")
    parser.add_argument(
        "--chapters",
        default="1-3",
        help="Chapter indices list/range (examples: 1-10, 1,2,5)",
    )
    parser.add_argument("--bearer-token", required=True, help="Supabase JWT bearer token")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=420,
        help="Per-chapter polling timeout",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Poll interval",
    )
    parser.add_argument(
        "--check-conflict",
        action="store_true",
        help="Probe duplicate generate conflict behavior",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
