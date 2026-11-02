from telegram import KeyboardButton, ReplyKeyboardMarkup

from config import config


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [config.MENU_TAXI, config.MENU_AUTO],
        [config.MENU_SERVICES, config.MENU_STORES],
        [config.MENU_MARKETS, config.MENU_PROPERTY],
        [config.MENU_MEMORY, config.MENU_SEARCH],
        [config.MENU_ADS, config.MENU_PRAYER],
        [config.MENU_CONTACT, config.MENU_ABOUT],
    ]
    if is_admin:
        rows.append([config.BTN_CONTROL])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[config.BTN_BACK], [config.BTN_MAIN_MENU]], resize_keyboard=True)


def prayer_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [config.BTN_NEXT_PRAYER, config.BTN_PRAYER_REMINDERS],
            [config.BTN_DHIKR, config.BTN_DAILY_DUA],
            [config.BTN_BACK],
            [config.BTN_MAIN_MENU],
        ],
        resize_keyboard=True,
    )
def taxi_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🏘 ХЎЖАОБОД ИЧИДА", "🏙 АНДИЖОН"],
            ["🛣 ТОШКЕНТ", "📍 БОШҚА ЙЎНАЛИШ"],
            ["📋 БУЮРТМАЛАРИМ", "🟢 МЕН ШОФЁРМАН"],
            [config.BTN_CANCEL],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Геолокацияни юбориш", request_location=True)], [config.BTN_CANCEL]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[config.BTN_CANCEL]], resize_keyboard=True)


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Телефон рақамни юбориш", request_contact=True)], [config.BTN_CANCEL]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["✅ Буюртмани тасдиқлаш"], [config.BTN_CANCEL]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
