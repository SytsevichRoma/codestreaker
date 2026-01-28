import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher

from app.core.config import settings
from app.core.logging import setup_logging
from app.db import repo
from app.bot.router import router
from app.services.scheduler import ReminderScheduler, set_scheduler_instance
from app.web.server import app as web_app

log = logging.getLogger(__name__)


async def run_bot(bot: Bot, dp: Dispatcher) -> None:
    await dp.start_polling(bot)


async def run_web() -> None:
    config = uvicorn.Config(web_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    setup_logging()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    if not settings.base_url:
        raise RuntimeError("BASE_URL is not set")
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not set")

    await repo.init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = ReminderScheduler(bot)
    set_scheduler_instance(scheduler)
    scheduler.start()
    await scheduler.schedule_all_users()

    await asyncio.gather(run_bot(bot, dp), run_web())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
