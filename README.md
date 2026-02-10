# CodeStreaker

Production-ready Telegram bot + Telegram Mini App (WebApp) MVP to track daily GitHub commits and LeetCode accepted submissions.

## Features
- Daily GitHub commits tracking via GitHub REST API events
- Daily LeetCode accepted submissions via GraphQL
- Goals, reminders, repo filters
- Streak tracking (current + best)
- Telegram WebApp dashboard with iOS-like UI

## Requirements
- Python 3.12
- Telegram bot token

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:
- `BOT_TOKEN` (required)
- `BOT_USERNAME` (required for WebApp quick actions)
- `BASE_URL` (public HTTPS URL for WebApp, e.g. https://your-domain.com)
- `SECRET_KEY` (used to validate WebApp initData; use a strong secret)
- `GITHUB_TOKEN` (optional, for higher rate limits)

## Run
```bash
python -m app.main
```

Web server runs on `http://0.0.0.0:8000`.

## Deploy on Render (Docker)
1. Create a new **Web Service**
2. Runtime: **Docker**
3. No Build/Start commands needed (Docker `CMD` runs the server)

Set env vars:
- `BOT_TOKEN`
- `SECRET_KEY`
- `GITHUB_TOKEN`
- `BOT_USERNAME`
- `BASE_URL`
- `DATABASE_URL` (Postgres; required to persist history/heatmap on Render)

Telegram requires HTTPS, so `BASE_URL` should be your Render URL.

### Render: set DATABASE_URL (Postgres) to persist history
Render’s default filesystem is ephemeral, so SQLite history resets on restarts. Provision a Postgres database and set `DATABASE_URL` to keep daily snapshots and heatmaps intact.

## Bot Commands
- `/start` - create user + show menu
- `/set` - set GitHub + LeetCode usernames (format: `github, leetcode`)
- `/connect_github` - set GitHub username
- `/connect_leetcode` - set LeetCode username
- `/repos` - set tracked repos (comma-separated owner/repo). Empty = any repo
- `/goals` - set daily goals
- `/reminders` - set reminder times
- `/status` - show today progress + streak

## Telegram WebApp Button
Set the bot menu button to open your WebApp:
1. Open **BotFather**
2. Select your bot → **Bot Settings** → **Menu Button**
3. Set URL to your `BASE_URL` (must be HTTPS)

## Notes
- Reminders run in the user timezone and are scheduled at configured times.
- The WebApp validates Telegram `initData` using `SECRET_KEY`.
