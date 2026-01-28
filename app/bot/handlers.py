import json
import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.config import settings
from app.db import repo
from app.bot.keyboards import main_menu
from app.services import github, leetcode, streaks
from app.services.timeutils import now_in_tz, parse_time_hhmm
from app.services.scheduler import scheduler_instance

log = logging.getLogger(__name__)

router = Router()


class SettingsState(StatesGroup):
    github = State()
    leetcode = State()
    repos = State()
    goals = State()
    reminders = State()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = await repo.get_user(message.from_user.id)
    if not user:
        await repo.create_user(message.from_user.id, settings.timezone_default)
    if scheduler_instance:
        await scheduler_instance.schedule_for_user(message.from_user.id)
    note = ""
    if not settings.base_url.startswith("https://"):
        note = "\nWebApp dashboard requires HTTPS. Use ngrok or set BASE_URL to an https URL."
    await message.answer(
        "Welcome to CodeStreaker!\nUse the buttons below or commands to configure." + note,
        reply_markup=main_menu(settings.base_url),
    )


@router.message(Command("connect_github"))
async def connect_github(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsState.github)
    await message.answer("Send your GitHub username:")


@router.message(SettingsState.github)
async def github_username_handler(message: Message, state: FSMContext) -> None:
    username = message.text.strip()
    await repo.set_github_username(message.from_user.id, username)
    await state.clear()
    await message.answer(f"✅ GitHub username saved: {username}")


@router.message(Command("connect_leetcode"))
async def connect_leetcode(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsState.leetcode)
    await message.answer("Send your LeetCode username:")


@router.message(SettingsState.leetcode)
async def leetcode_username_handler(message: Message, state: FSMContext) -> None:
    username = message.text.strip()
    await repo.set_leetcode_username(message.from_user.id, username)
    await state.clear()
    await message.answer(f"✅ LeetCode username saved: {username}")


@router.message(Command("repos"))
async def repos_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsState.repos)
    await message.answer("Send repos as comma-separated owner/repo. Empty = any repo.")


@router.message(SettingsState.repos)
async def repos_save_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    repos = [r.strip() for r in text.split(",") if r.strip()] if text else []
    await repo.set_repos(message.from_user.id, repos)
    await state.clear()
    await message.answer("✅ Repos updated")


@router.message(Command("goals"))
async def goals_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsState.goals)
    await message.answer("Send goals as: commits_per_day, leetcode_per_day (example: 2,2)")


@router.message(SettingsState.goals)
async def goals_save_handler(message: Message, state: FSMContext) -> None:
    try:
        parts = [p.strip() for p in message.text.replace(" ", "").split(",") if p.strip()]
        if len(parts) != 2:
            raise ValueError("invalid")
        goals = {"github_commits": int(parts[0]), "leetcode_solved": int(parts[1])}
        await repo.set_goals(message.from_user.id, goals)
        await state.clear()
        await message.answer("✅ Goals updated")
    except Exception:
        await message.answer("Invalid format. Example: 2,2")


@router.message(Command("reminders"))
async def reminders_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsState.reminders)
    await message.answer("Send reminders as HH:MM,HH:MM (Europe/Kyiv). Example: 10:00,21:30")


@router.message(SettingsState.reminders)
async def reminders_save_handler(message: Message, state: FSMContext) -> None:
    try:
        parts = [p.strip() for p in message.text.split(",") if p.strip()]
        reminders = [parse_time_hhmm(p) for p in parts]
        await repo.set_reminders(message.from_user.id, reminders)
        if scheduler_instance:
            await scheduler_instance.schedule_for_user(message.from_user.id)
        await state.clear()
        await message.answer("✅ Reminders updated")
    except Exception:
        await message.answer("Invalid format. Example: 10:00,21:30")


@router.message(Command("status"))
async def status_handler(message: Message) -> None:
    await _send_status(message)


@router.message(F.text == "✅ Status")
async def status_button_handler(message: Message) -> None:
    await _send_status(message)


@router.message(F.text == "⚙️ Settings")
async def settings_button_handler(message: Message) -> None:
    await message.answer(
        "Use commands:\n"
        "/connect_github\n/connect_leetcode\n/repos\n/goals\n/reminders"
    )


async def _send_status(message: Message) -> None:
    user = await repo.get_user(message.from_user.id)
    if not user:
        user = await repo.create_user(message.from_user.id, settings.timezone_default)
    tz_name = user["tz"]
    goals = json.loads(user["goals_json"])
    repos = json.loads(user["repos_json"])
    gh_user = user.get("github_username")
    lc_user = user.get("leetcode_username")

    github_commits = 0
    leetcode_solved = 0
    if gh_user:
        github_commits = await github.count_commits_today(gh_user, tz_name, repos)
    if lc_user:
        leetcode_solved = await leetcode.count_accepted_today(lc_user, tz_name)

    today = now_in_tz(tz_name).date()
    await repo.upsert_daily_stats(
        message.from_user.id,
        today.isoformat(),
        github_commits,
        leetcode_solved,
    )
    streak_info = await streaks.update_streak_for_date(
        message.from_user.id,
        today,
        goals,
        {"github_commits": github_commits, "leetcode_solved": leetcode_solved},
    )

    text = (
        f"📅 {today.isoformat()} ({tz_name})\n"
        f"GitHub commits: {github_commits}/{goals['github_commits']}\n"
        f"LeetCode solved: {leetcode_solved}/{goals['leetcode_solved']}\n"
        f"Streak: {streak_info['current_streak']} (best {streak_info['best_streak']})"
    )
    await message.answer(text)
