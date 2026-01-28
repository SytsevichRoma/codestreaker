import asyncio
import logging
from datetime import timezone, datetime
from zoneinfo import ZoneInfo
import httpx

log = logging.getLogger(__name__)

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"

QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    timestamp
  }
}
"""


async def _request_recent(username: str, limit: int = 20) -> list[dict]:
    payload = {"query": QUERY, "variables": {"username": username, "limit": limit}}
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(3):
            try:
                resp = await client.post(LEETCODE_GRAPHQL, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", {}).get("recentAcSubmissionList", [])
            except Exception as exc:
                log.warning("LeetCode API error: %s", exc)
                await asyncio.sleep(1 + attempt)
    return []


def _is_today(ts: str, tz_name: str) -> bool:
    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone(ZoneInfo(tz_name))
    today = datetime.now(ZoneInfo(tz_name)).date()
    return dt.date() == today


async def count_accepted_today(username: str, tz_name: str) -> int:
    submissions = await _request_recent(username)
    total = 0
    for sub in submissions:
        if _is_today(sub.get("timestamp", "0"), tz_name):
            total += 1
    return total
