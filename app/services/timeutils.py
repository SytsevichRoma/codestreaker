import hmac
import hashlib
import urllib.parse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any


def now_in_tz(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def date_str_in_tz(dt: datetime, tz_name: str) -> str:
    return dt.astimezone(ZoneInfo(tz_name)).date().isoformat()


def parse_time_hhmm(value: str) -> str:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("Invalid time format")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Invalid time value")
    return f"{hour:02d}:{minute:02d}"


def validate_init_data(init_data: str, secret_key: str) -> dict[str, Any]:
    parsed = urllib.parse.parse_qs(init_data, strict_parsing=True)
    if "hash" not in parsed:
        raise ValueError("Missing hash")
    hash_value = parsed["hash"][0]
    data_pairs = []
    for key in sorted(k for k in parsed.keys() if key != "hash"):
        data_pairs.append(f"{key}={parsed[key][0]}")
    data_check_string = "\n".join(data_pairs)
    secret = hashlib.sha256(secret_key.encode("utf-8")).digest()
    computed = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if computed != hash_value:
        raise ValueError("Invalid initData hash")
    user_json = parsed.get("user", ["{}"])[0]
    user = urllib.parse.unquote(user_json)
    return {"user": user, "raw": parsed}


def unix_to_tz_date(ts: int, tz_name: str) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo(tz_name)).date().isoformat()
