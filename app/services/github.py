import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Iterable

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "CodeStreaker"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def _request_events(username: str) -> list[dict]:
    url = f"https://api.github.com/users/{username}/events"
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, headers=_headers())
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, list) else []
            except Exception as exc:
                log.warning("GitHub API error: %s", exc)
                await asyncio.sleep(1 + attempt)
    return []


def _event_in_local_day(created_at: str, start_utc: datetime, end_utc: datetime) -> bool:
    try:
        event_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
    return start_utc <= event_dt < end_utc


def _filter_repos(repo_name: str, repos: Iterable[str]) -> bool:
    if not repos:
        return True
    return repo_name in set(repos)


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


async def _count_commits_via_compare(repo_full: str, before: str, head: str) -> int:
    """
    Fallback when PushEvent payload doesn't include commits/size/distinct_size.
    Uses: GET /repos/{owner}/{repo}/compare/{before}...{head}
    """
    if not repo_full or "/" not in repo_full or not before or not head:
        return 0

    owner, repo = repo_full.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{repo}/compare/{before}...{head}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        data = resp.json()

    # GitHub compare response usually has 'ahead_by' and 'commits' list
    ahead_by = _to_int(data.get("ahead_by"), 0)
    if ahead_by > 0:
        return ahead_by

    commits = data.get("commits")
    if isinstance(commits, list):
        return len(commits)

    return 0


async def count_commits_today(username: str, tz_name: str, repos: list[str]) -> int:
    events = await _request_events(username)

    tz = ZoneInfo(tz_name)
    today_local = datetime.now(tz).date()
    start_local = datetime.combine(today_local, datetime.min.time(), tzinfo=tz)
    end_local = start_local + timedelta(days=1)

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    repo_set = set(r.strip() for r in repos if r and r.strip())

    total = 0
    push_events_today = 0

    methods_list = 0
    methods_distinct = 0
    methods_size = 0
    methods_compare = 0

    for event in events:
        if event.get("type") != "PushEvent":
            continue

        if not _event_in_local_day(event.get("created_at", ""), start_utc, end_utc):
            continue

        repo = (event.get("repo") or {}).get("name", "")
        if repo_set and repo not in repo_set:
            continue

        payload = event.get("payload") or {}

        commits_list = payload.get("commits") or []
        if isinstance(commits_list, list) and len(commits_list) > 0:
            c = len(commits_list)
            methods_list += 1
        else:
            distinct = payload.get("distinct_size")
            distinct_int = _to_int(distinct, 0)

            if distinct_int > 0:
                c = distinct_int
                methods_distinct += 1
            else:
                size_val = payload.get("size")
                size_int = _to_int(size_val, 0)
                if size_int > 0:
                    c = size_int
                    methods_size += 1
                else:
                    # ✅ NEW: compare fallback using before/head
                    before = payload.get("before") or ""
                    head = payload.get("head") or ""
                    try:
                        c = await _count_commits_via_compare(repo, before, head)
                    except Exception as exc:
                        log.warning("GitHub compare API error: %s", exc)
                        c = 0
                    methods_compare += 1

        total += c
        push_events_today += 1
        log.info("GitHub push event commits: %d", c)

    log.info(
        "GitHub commits today: kyiv_date=%s start_utc=%s end_utc=%s events=%d push_events_today=%d commits=%d "
        "methods=list:%d distinct_size:%d size:%d compare:%d",
        today_local.isoformat(),
        start_utc.isoformat(),
        end_utc.isoformat(),
        len(events),
        push_events_today,
        total,
        methods_list,
        methods_distinct,
        methods_size,
        methods_compare,
    )
    return total
