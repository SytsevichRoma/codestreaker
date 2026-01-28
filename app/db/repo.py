import json
from datetime import datetime
from pathlib import Path
from typing import Any
import aiosqlite

from app.core.config import settings

DEFAULT_GOALS = {"github_commits": 2, "leetcode_solved": 2}
DEFAULT_REMINDERS = ["10:00", "21:30"]
DEFAULT_REPOS: list[str] = []


async def init_db() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    async with aiosqlite.connect(settings.database_path) as db:
        with schema_path.open("r", encoding="utf-8") as f:
            await db.executescript(f.read())
        await db.commit()


async def fetchone(sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row


async def fetchall(sql: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    row = await fetchone(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    return dict(row) if row else None


async def create_user(telegram_id: int, tz: str) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    goals = json.dumps(DEFAULT_GOALS)
    reminders = json.dumps(DEFAULT_REMINDERS)
    repos = json.dumps(DEFAULT_REPOS)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, tz, github_username, leetcode_username, goals_json, reminders_json, repos_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                telegram_id,
                tz,
                settings.default_github_username,
                settings.default_leetcode_username,
                goals,
                reminders,
                repos,
                now,
            ),
        )
        await db.execute(
            "INSERT OR IGNORE INTO streaks (telegram_id, current_streak, best_streak, last_success_date) VALUES (?, 0, 0, NULL)",
            (telegram_id,),
        )
        await db.commit()
    user = await get_user(telegram_id)
    assert user
    return user


async def update_user_fields(telegram_id: int, **fields: Any) -> None:
    if not fields:
        return
    keys = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values())
    values.append(telegram_id)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(f"UPDATE users SET {keys} WHERE telegram_id = ?", values)
        await db.commit()


async def set_github_username(telegram_id: int, username: str) -> None:
    await update_user_fields(telegram_id, github_username=username)


async def set_leetcode_username(telegram_id: int, username: str) -> None:
    await update_user_fields(telegram_id, leetcode_username=username)


async def set_goals(telegram_id: int, goals: dict[str, int]) -> None:
    await update_user_fields(telegram_id, goals_json=json.dumps(goals))


async def set_reminders(telegram_id: int, reminders: list[str]) -> None:
    await update_user_fields(telegram_id, reminders_json=json.dumps(reminders))


async def set_repos(telegram_id: int, repos: list[str]) -> None:
    await update_user_fields(telegram_id, repos_json=json.dumps(repos))


async def get_daily_stats(telegram_id: int, date: str) -> dict[str, Any] | None:
    row = await fetchone(
        "SELECT * FROM daily_stats WHERE telegram_id = ? AND date = ?",
        (telegram_id, date),
    )
    return dict(row) if row else None


async def upsert_daily_stats(
    telegram_id: int,
    date: str,
    github_commits: int,
    leetcode_solved: int,
) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO daily_stats (telegram_id, date, github_commits, leetcode_solved) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(telegram_id, date) DO UPDATE SET github_commits = excluded.github_commits, leetcode_solved = excluded.leetcode_solved",
            (telegram_id, date, github_commits, leetcode_solved),
        )
        await db.commit()


async def get_streaks(telegram_id: int) -> dict[str, Any] | None:
    row = await fetchone(
        "SELECT * FROM streaks WHERE telegram_id = ?",
        (telegram_id,),
    )
    return dict(row) if row else None


async def update_streaks(
    telegram_id: int,
    current_streak: int,
    best_streak: int,
    last_success_date: str | None,
) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE streaks SET current_streak = ?, best_streak = ?, last_success_date = ? WHERE telegram_id = ?",
            (current_streak, best_streak, last_success_date, telegram_id),
        )
        await db.commit()
