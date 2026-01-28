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


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    try:
        parsed = urllib.parse.parse_qs(
            init_data,
            strict_parsing=True,
            keep_blank_values=True,
        )
    except ValueError as exc:
        raise ValueError("parse_error") from exc

    if "hash" not in parsed or not parsed["hash"]:
        raise ValueError("missing_hash")
    hash_value = parsed["hash"][0]

    data_pairs = []
    for key in sorted(k for k in parsed.keys() if k != "hash"):
        value = parsed[key][0]
        data_pairs.append(f"{key}={value}")
    data_check_string = "\n".join(data_pairs)

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(computed, hash_value):
        raise ValueError("hash_mismatch")

    if max_age_seconds is not None:
        auth_date_raw = parsed.get("auth_date", [None])[0]
        if auth_date_raw is None:
            raise ValueError("missing_auth_date")
        try:
            auth_date = int(auth_date_raw)
        except ValueError as exc:
            raise ValueError("invalid_auth_date") from exc
        if datetime.now(timezone.utc).timestamp() - auth_date > max_age_seconds:
            raise ValueError("auth_date_expired")

    user_json = parsed.get("user", ["{}"])[0]
    user = urllib.parse.unquote(user_json)
    return {"user": user, "raw": parsed}


def unix_to_tz_date(ts: int, tz_name: str) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo(tz_name)).date().isoformat()
