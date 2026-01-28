from datetime import date, timedelta
from typing import Any

from app.db import repo


def _goals_met(goals: dict[str, int], stats: dict[str, int]) -> bool:
    return (
        stats.get("github_commits", 0) >= goals.get("github_commits", 0)
        and stats.get("leetcode_solved", 0) >= goals.get("leetcode_solved", 0)
    )


async def update_streak_for_date(
    telegram_id: int,
    current_date: date,
    goals: dict[str, int],
    stats: dict[str, int],
) -> dict[str, Any]:
    streaks = await repo.get_streaks(telegram_id)
    if not streaks:
        await repo.update_streaks(telegram_id, 0, 0, None)
        streaks = await repo.get_streaks(telegram_id)
    assert streaks

    last_success = streaks.get("last_success_date")
    current = int(streaks.get("current_streak", 0))
    best = int(streaks.get("best_streak", 0))

    if not _goals_met(goals, stats):
        return {"current_streak": current, "best_streak": best, "last_success_date": last_success}

    last_success_date = date.fromisoformat(last_success) if last_success else None
    if last_success_date == current_date:
        return {"current_streak": current, "best_streak": best, "last_success_date": last_success}

    if last_success_date == current_date - timedelta(days=1):
        current += 1
    else:
        current = 1
    if current > best:
        best = current

    await repo.update_streaks(telegram_id, current, best, current_date.isoformat())
    return {"current_streak": current, "best_streak": best, "last_success_date": current_date.isoformat()}
