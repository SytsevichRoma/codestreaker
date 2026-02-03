import json
import logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from app.db import repo
from app.services import github, leetcode, streaks
from app.services.timeutils import now_in_tz

log = logging.getLogger(__name__)

scheduler_instance: "ReminderScheduler | None" = None


def set_scheduler_instance(instance: "ReminderScheduler") -> None:
    global scheduler_instance
    scheduler_instance = instance


class ReminderScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown()

    async def schedule_for_user(self, telegram_id: int) -> None:
        user = await repo.get_user(telegram_id)
        if not user:
            return
        reminders = json.loads(user["reminders_json"])
        tz_name = user["tz"]

        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"reminder:{telegram_id}:"):
                self.scheduler.remove_job(job.id)

        for time_str in reminders:
            job_id = f"reminder:{telegram_id}:{time_str}"
            hour, minute = map(int, time_str.split(":"))
            self.scheduler.add_job(
                self._run_reminder,
                "cron",
                id=job_id,
                hour=hour,
                minute=minute,
                timezone=ZoneInfo(tz_name),
                args=[telegram_id],
                replace_existing=True,
            )

    async def schedule_all_users(self) -> None:
        rows = await repo.fetchall("SELECT telegram_id FROM users")
        for row in rows:
            await self.schedule_for_user(int(row["telegram_id"]))

    async def _run_reminder(self, telegram_id: int) -> None:
        user = await repo.get_user(telegram_id)
        if not user:
            return
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
            telegram_id,
            today.isoformat(),
            github_commits,
            leetcode_solved,
        )
        await streaks.update_streak_for_date(
            telegram_id,
            today,
            goals,
            {"github_commits": github_commits, "leetcode_solved": leetcode_solved},
        )

        gh_goal = int(goals.get("github_commits", 0))
        lc_goal = int(goals.get("leetcode_solved", 0))
        gh_left = max(gh_goal - int(github_commits), 0)
        lc_left = max(lc_goal - int(leetcode_solved), 0)

        if gh_left == 0 and lc_left == 0:
            log.info("Reminder skipped: goals completed for %s on %s", telegram_id, today.isoformat())
            return

        msg = (
            "⏰ Quick reminder\n"
            f"GitHub: {gh_left} commit{'s' if gh_left != 1 else ''} left\n"
            f"LeetCode: {lc_left} solve{'s' if lc_left != 1 else ''} left"
        )
        try:
            await self.bot.send_message(telegram_id, msg)
        except Exception as exc:
            log.warning("Failed to send reminder: %s", exc)
