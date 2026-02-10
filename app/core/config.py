import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    bot_username: str
    github_token: str | None
    base_url: str
    secret_key: str
    database_url: str | None
    database_path: str
    timezone_default: str


_def_tz = "Europe/Kyiv"


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", "").strip(),
    bot_username=os.getenv("BOT_USERNAME", "").strip(),
    github_token=os.getenv("GITHUB_TOKEN", "").strip() or None,
    base_url=os.getenv("BASE_URL", "").strip(),
    secret_key=os.getenv("SECRET_KEY", "").strip(),
    database_url=os.getenv("DATABASE_URL", "").strip() or None,
    database_path=os.getenv("DATABASE_PATH", "./codestreaker.db"),
    timezone_default=os.getenv("DEFAULT_TIMEZONE", _def_tz),
)
