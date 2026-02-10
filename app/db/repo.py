import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
import asyncpg

from app.core.config import settings

DEFAULT_GOALS = {"github_commits": 2, "leetcode_solved": 2}
DEFAULT_REMINDERS = ["10:00", "21:30"]
DEFAULT_REPOS: list[str] = []
DEFAULT_AVATAR = "🐶"
_pg_pool: asyncpg.Pool | None = None


def _is_postgres() -> bool:
    return bool(settings.database_url)


async def _ensure_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not set for Postgres connection")
        _pg_pool = await asyncpg.create_pool(settings.database_url)
    return _pg_pool


def _param(index: int) -> str:
    return f"${index}" if _is_postgres() else "?"


async def _execute_schema_postgres(schema_sql: str) -> None:
    pool = await _ensure_pg_pool()
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
    async with pool.acquire() as conn:
        for stmt in statements:
            await conn.execute(stmt)


async def init_db() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    with schema_path.open("r", encoding="utf-8") as f:
        schema_sql = f.read()
    if _is_postgres():
        await _execute_schema_postgres(schema_sql)
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
            )
            columns = {row["column_name"] for row in rows}
            for col in ("github_username", "leetcode_username", "avatar"):
                if col not in columns:
                    await conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    else:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.executescript(schema_sql)
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in await cursor.fetchall()]
            await cursor.close()
            for col in ("github_username", "leetcode_username", "avatar"):
                if col not in columns:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            await db.commit()


async def fetchone(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    if _is_postgres():
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
            return dict(row) if row else None
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None


async def fetchall(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    if _is_postgres():
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    return await fetchone(
        f"SELECT * FROM users WHERE telegram_id = {_param(1)}",
        (telegram_id,),
    )


async def create_user_if_missing(
    telegram_id: int,
    tz: str,
    tg_username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    _ = (tg_username, first_name, last_name)
    now = datetime.utcnow().isoformat()
    goals = json.dumps(DEFAULT_GOALS)
    reminders = json.dumps(DEFAULT_REMINDERS)
    repos = json.dumps(DEFAULT_REPOS)
    if _is_postgres():
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (telegram_id, tz, github_username, leetcode_username, avatar, goals_json, reminders_json, repos_json, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                "ON CONFLICT (telegram_id) DO NOTHING",
                telegram_id,
                tz,
                None,
                None,
                DEFAULT_AVATAR,
                goals,
                reminders,
                repos,
                now,
            )
            await conn.execute(
                "INSERT INTO streaks (telegram_id, current_streak, best_streak, last_success_date) "
                "VALUES ($1, 0, 0, NULL) "
                "ON CONFLICT (telegram_id) DO NOTHING",
                telegram_id,
            )
    else:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (telegram_id, tz, github_username, leetcode_username, avatar, goals_json, reminders_json, repos_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    telegram_id,
                    tz,
                    None,
                    None,
                    DEFAULT_AVATAR,
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
    keys = list(fields.keys())
    set_clause = ", ".join(f"{k} = {_param(i + 1)}" for i, k in enumerate(keys))
    values = list(fields.values())
    values.append(telegram_id)
    where_param = _param(len(values))
    sql = f"UPDATE users SET {set_clause} WHERE telegram_id = {where_param}"
    if _is_postgres():
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(sql, *values)
    else:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(sql, values)
            await db.commit()


async def set_github_username(telegram_id: int, username: str) -> None:
    await update_user_fields(telegram_id, github_username=username)


async def set_leetcode_username(telegram_id: int, username: str) -> None:
    await update_user_fields(telegram_id, leetcode_username=username)


async def update_user_handles(
    telegram_id: int,
    github_username: str | None,
    leetcode_username: str | None,
) -> None:
    await update_user_fields(
        telegram_id,
        github_username=github_username,
        leetcode_username=leetcode_username,
    )


async def set_goals(telegram_id: int, goals: dict[str, int]) -> None:
    await update_user_fields(telegram_id, goals_json=json.dumps(goals))


async def set_reminders(telegram_id: int, reminders: list[str]) -> None:
    await update_user_fields(telegram_id, reminders_json=json.dumps(reminders))


async def set_repos(telegram_id: int, repos: list[str]) -> None:
    await update_user_fields(telegram_id, repos_json=json.dumps(repos))


async def get_daily_stats(telegram_id: int, date: str) -> dict[str, Any] | None:
    return await fetchone(
        f"SELECT * FROM daily_stats WHERE telegram_id = {_param(1)} AND date = {_param(2)}",
        (telegram_id, date),
    )


async def get_daily_stats_range(
    telegram_id: int,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    return await fetchall(
        f"SELECT * FROM daily_stats WHERE telegram_id = {_param(1)} AND date BETWEEN {_param(2)} AND {_param(3)} ORDER BY date ASC",
        (telegram_id, start_date, end_date),
    )


async def upsert_daily_stats(
    telegram_id: int,
    date: str,
    github_commits: int,
    leetcode_solved: int,
) -> None:
    if _is_postgres():
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO daily_stats (telegram_id, date, github_commits, leetcode_solved) VALUES ($1, $2, $3, $4) "
                "ON CONFLICT(telegram_id, date) DO UPDATE SET github_commits = EXCLUDED.github_commits, leetcode_solved = EXCLUDED.leetcode_solved",
                telegram_id,
                date,
                github_commits,
                leetcode_solved,
            )
    else:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "INSERT INTO daily_stats (telegram_id, date, github_commits, leetcode_solved) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(telegram_id, date) DO UPDATE SET github_commits = excluded.github_commits, leetcode_solved = excluded.leetcode_solved",
                (telegram_id, date, github_commits, leetcode_solved),
            )
            await db.commit()


async def get_streaks(telegram_id: int) -> dict[str, Any] | None:
    return await fetchone(
        f"SELECT * FROM streaks WHERE telegram_id = {_param(1)}",
        (telegram_id,),
    )


async def update_streaks(
    telegram_id: int,
    current_streak: int,
    best_streak: int,
    last_success_date: str | None,
) -> None:
    sql = (
        "UPDATE streaks SET current_streak = "
        f"{_param(1)}, best_streak = {_param(2)}, last_success_date = {_param(3)} "
        f"WHERE telegram_id = {_param(4)}"
    )
    values = (current_streak, best_streak, last_success_date, telegram_id)
    if _is_postgres():
        pool = await _ensure_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(sql, *values)
    else:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(sql, values)
            await db.commit()
