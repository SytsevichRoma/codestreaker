import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Iterable
import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


async def _request_events(username: str) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    url = f"https://api.github.com/users/{username}/events"
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                log.warning("GitHub API error: %s", exc)
                await asyncio.sleep(1 + attempt)
    return []


def _is_today(created_at: str, tz_name: str) -> bool:
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    local_date = dt.astimezone(ZoneInfo(tz_name)).date()
    today = datetime.now(ZoneInfo(tz_name)).date()
    return local_date == today


def _filter_repos(repo_name: str, repos: Iterable[str]) -> bool:
    if not repos:
        return True
    return repo_name in set(repos)


async def count_commits_today(username: str, tz_name: str, repos: list[str]) -> int:
    events = await _request_events(username)
    total = 0
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        if not _is_today(event.get("created_at", ""), tz_name):
            continue
        repo = event.get("repo", {}).get("name", "")
        if not _filter_repos(repo, repos):
            continue
        payload = event.get("payload", {})
        commits = payload.get("commits", [])
        total += len(commits)
    return total
