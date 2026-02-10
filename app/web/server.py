import json
import logging
import urllib.parse
import asyncio
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.db import repo
from app.services import github, leetcode, streaks
from app.services.timeutils import now_in_tz, parse_time_hhmm, validate_init_data
from app.services.scheduler import scheduler_instance

log = logging.getLogger(__name__)

base_dir = Path(__file__).resolve().parent
app = FastAPI()
app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

templates = Jinja2Templates(directory=str(base_dir / "templates"))

_STATUS_TTL_SECONDS = 25
_STATUS_CACHE: dict[tuple[int, str, str], tuple[int, float]] = {}


@app.on_event("startup")
async def startup() -> None:
    await repo.init_db()


def _cache_get(key: tuple[int, str, str]) -> int | None:
    entry = _STATUS_CACHE.get(key)
    if not entry:
        return None
    value, ts = entry
    if time.time() - ts > _STATUS_TTL_SECONDS:
        _STATUS_CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: tuple[int, str, str], value: int) -> None:
    _STATUS_CACHE[key] = (int(value), time.time())


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _normalize_handle(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


async def _get_init_data(request: Request) -> str:
    init_data = request.query_params.get("initData")
    if init_data:
        return init_data
    for header_name in ("X-Telegram-Init-Data", "X-Init-Data"):
        init_data = request.headers.get(header_name)
        if init_data:
            return init_data
    body = await request.body()
    if not body:
        return ""
    try:
        payload = await request.json()
        if isinstance(payload, dict):
            init_data = payload.get("initData")
            if init_data:
                return init_data
    except Exception:
        pass
    try:
        parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return parsed.get("initData", [""])[0]
    except Exception:
        return ""


async def _get_user_from_init(request: Request) -> dict[str, Any]:
    init_data = await _get_init_data(request)
    if not init_data:
        log.warning("initData validation failed: missing_init_data")
        raise HTTPException(status_code=401, detail="Missing initData")
    try:
        parsed = validate_init_data(init_data, settings.bot_token)
        user_raw = parsed["raw"].get("user", ["{}"])[0]
        user = json.loads(user_raw)
        return user
    except ValueError as exc:
        reason = str(exc) or "validation_error"
        log.warning("initData validation failed: %s", reason)
        raise HTTPException(status_code=401, detail="Invalid initData") from exc
    except Exception as exc:
        log.warning("initData validation failed: unexpected_error:%s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="Invalid initData") from exc


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "base_url": settings.base_url,
            "bot_username": settings.bot_username,
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "base_url": settings.base_url,
            "bot_username": settings.bot_username,
        },
    )


@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "base_url": settings.base_url,
            "bot_username": settings.bot_username,
        },
    )


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(base_dir / "static" / "favicon.ico", media_type="image/x-icon")


@app.get("/api/status")
async def api_status(request: Request):
    user = await _get_user_from_init(request)
    telegram_id = int(user["id"])
    db_user = await repo.get_user(telegram_id)
    if not db_user:
        db_user = await repo.create_user_if_missing(
            telegram_id,
            settings.timezone_default,
            user.get("username"),
            user.get("first_name"),
            user.get("last_name"),
        )

    force = _is_truthy(request.query_params.get("force"))
    tz_name = db_user["tz"]
    goals = json.loads(db_user["goals_json"])
    repos = json.loads(db_user["repos_json"])
    gh_user = _normalize_handle(db_user.get("github_username"))
    lc_user = _normalize_handle(db_user.get("leetcode_username"))

    if not gh_user or not lc_user:
        return JSONResponse(
            {
                "needs_setup": True,
                "github_username": gh_user,
                "leetcode_username": lc_user,
                "timezone": tz_name,
                "avatar": db_user.get("avatar"),
            }
        )

    today = now_in_tz(tz_name).date()
    today_str = today.isoformat()
    gh_key = (telegram_id, today_str, "github_commits")
    lc_key = (telegram_id, today_str, "leetcode_solved")

    github_commits = None
    leetcode_solved = None
    if not force:
        if gh_user:
            github_commits = _cache_get(gh_key)
        if lc_user:
            leetcode_solved = _cache_get(lc_key)

    tasks: list[tuple[str, Any]] = []
    if gh_user and github_commits is None:
        tasks.append(("github", github.count_commits_today(gh_user, tz_name, repos)))
    if lc_user and leetcode_solved is None:
        tasks.append(("leetcode", leetcode.count_accepted_today(lc_user, tz_name)))

    if tasks:
        results = await asyncio.gather(*(task for _, task in tasks))
        for (key, _), value in zip(tasks, results):
            if key == "github":
                github_commits = int(value)
                _cache_set(gh_key, github_commits)
            elif key == "leetcode":
                leetcode_solved = int(value)
                _cache_set(lc_key, leetcode_solved)

    if github_commits is None:
        github_commits = 0
    if leetcode_solved is None:
        leetcode_solved = 0
    await repo.upsert_daily_stats(
        telegram_id,
        today_str,
        github_commits,
        leetcode_solved,
    )
    streak_info = await streaks.update_streak_for_date(
        telegram_id,
        today,
        goals,
        {"github_commits": github_commits, "leetcode_solved": leetcode_solved},
    )

    return JSONResponse(
        {
            "needs_setup": False,
            "date": today.isoformat(),
            "timezone": tz_name,
            "github_commits": github_commits,
            "leetcode_solved": leetcode_solved,
            "goals": goals,
            "reminders": json.loads(db_user["reminders_json"]),
            "repos": repos,
            "streak": streak_info,
            "avatar": db_user.get("avatar"),
            "github_username": gh_user,
            "leetcode_username": lc_user,
        }
    )


@app.get("/api/history")
async def api_history(request: Request, days: int = 7, init_data: str | None = Query(None, alias="initData")):
    user = await _get_user_from_init(request)
    telegram_id = int(user["id"])
    db_user = await repo.get_user(telegram_id)
    if not db_user:
        db_user = await repo.create_user_if_missing(
            telegram_id,
            settings.timezone_default,
            user.get("username"),
            user.get("first_name"),
            user.get("last_name"),
        )

    tz_name = db_user["tz"]
    gh_user = _normalize_handle(db_user.get("github_username"))
    lc_user = _normalize_handle(db_user.get("leetcode_username"))
    if not gh_user or not lc_user:
        return JSONResponse({"needs_setup": True, "timezone": tz_name})
    safe_days = max(1, min(int(days or 7), 31))
    today = now_in_tz(tz_name).date()
    start_date = today - timedelta(days=safe_days - 1)

    rows = await repo.get_daily_stats_range(
        telegram_id,
        start_date.isoformat(),
        today.isoformat(),
    )
    row_map = {row["date"]: row for row in rows}
    days_out = []
    for i in range(safe_days):
        date = (start_date + timedelta(days=i)).isoformat()
        row = row_map.get(date)
        days_out.append(
            {
                "date": date,
                "github": int(row["github_commits"]) if row else 0,
                "leetcode": int(row["leetcode_solved"]) if row else 0,
            }
        )

    return JSONResponse({"tz": tz_name, "days": days_out})


@app.get("/api/health")
async def api_health():
    db_ok = True
    try:
        await repo.fetchone("SELECT 1")
    except Exception:
        db_ok = False
    return JSONResponse(
        {
            "ok": db_ok,
            "db": db_ok,
            "time": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/healthz")
async def healthz():
    db_ok = True
    try:
        await repo.fetchone("SELECT 1")
    except Exception:
        db_ok = False
    return JSONResponse(
        {
            "ok": db_ok,
            "db": db_ok,
            "time": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.post("/api/settings")
async def api_settings(request: Request):
    user = await _get_user_from_init(request)
    telegram_id = int(user["id"])
    payload = await request.json()
    db_user = await repo.get_user(telegram_id)
    if not db_user:
        await repo.create_user_if_missing(
            telegram_id,
            settings.timezone_default,
            user.get("username"),
            user.get("first_name"),
            user.get("last_name"),
        )

    updates: dict[str, Any] = {}
    reminders_changed = False
    if "goals" in payload:
        goals = payload["goals"]
        updates["goals_json"] = json.dumps(
            {
                "github_commits": int(goals.get("github_commits", 2)),
                "leetcode_solved": int(goals.get("leetcode_solved", 2)),
            }
        )
    if "reminders" in payload:
        reminders = [parse_time_hhmm(r) for r in payload["reminders"]]
        updates["reminders_json"] = json.dumps(reminders)
        reminders_changed = True
    if "repos" in payload:
        repos = [r.strip() for r in payload["repos"] if r.strip()]
        updates["repos_json"] = json.dumps(repos)
    if "github_username" in payload:
        updates["github_username"] = _normalize_handle(payload.get("github_username"))
    if "leetcode_username" in payload:
        updates["leetcode_username"] = _normalize_handle(payload.get("leetcode_username"))
    if "avatar" in payload:
        updates["avatar"] = payload["avatar"]

    if updates:
        await repo.update_user_fields(telegram_id, **updates)
        if reminders_changed and scheduler_instance:
            await scheduler_instance.schedule_for_user(telegram_id)

    return JSONResponse({"ok": True})
