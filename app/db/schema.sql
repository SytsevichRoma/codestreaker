CREATE TABLE IF NOT EXISTS users (
  telegram_id INTEGER PRIMARY KEY,
  tz TEXT NOT NULL,
  github_username TEXT,
  leetcode_username TEXT,
  avatar TEXT,
  goals_json TEXT NOT NULL,
  reminders_json TEXT NOT NULL,
  repos_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_stats (
  telegram_id INTEGER NOT NULL,
  date TEXT NOT NULL,
  github_commits INTEGER NOT NULL,
  leetcode_solved INTEGER NOT NULL,
  PRIMARY KEY (telegram_id, date)
);

CREATE TABLE IF NOT EXISTS streaks (
  telegram_id INTEGER PRIMARY KEY,
  current_streak INTEGER NOT NULL,
  best_streak INTEGER NOT NULL,
  last_success_date TEXT
);
