from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def main_menu(base_url: str) -> ReplyKeyboardMarkup:
    dashboard_button: KeyboardButton
    if base_url.startswith("https://"):
        dashboard_button = KeyboardButton(text="📱 Dashboard", web_app=WebAppInfo(url=base_url))
    else:
        dashboard_button = KeyboardButton(text="📱 Dashboard", url=base_url)
    return ReplyKeyboardMarkup(
        keyboard=[
            [dashboard_button],
            [KeyboardButton(text="✅ Status"), KeyboardButton(text="⚙️ Settings")],
        ],
        resize_keyboard=True,
    )
