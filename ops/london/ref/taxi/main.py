import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram import Update
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.database import init_db, set_bot_user_active
from bot.handlers.about import about_handler
from bot.handlers.auto_services import auto_services_handlers
from bot.handlers.admin import admin_handler, daily_dua_admin_handlers
from bot.handlers.ads import ads_handlers, ads_section
from bot.handlers.contact import contact_handler
from bot.handlers.content import content_handlers
from bot.handlers.daily_dua import daily_dua_handler
from bot.handlers.dhikr import dhikr_callback_handler, dhikr_handler
from bot.handlers.drivers import driver_handlers
from bot.handlers.driver_profiles import driver_profile_conversation
from bot.handlers.menu import main_menu_command, menu_handler
from bot.handlers.memory import memory_handlers
from bot.handlers.prayer import next_prayer_handler, prayer_handler
from bot.handlers.reminders import reminder_toggle_handler, reminders_handler
from bot.handlers.search import search_handler
from bot.handlers.services import service_handlers
from bot.handlers.taxi import claim_handler, rating_handlers, taxi_conversation
from bot.handlers.users import user_tracker_handler
from bot.services.daily_dua import daily_dua_loop
from bot.services.prayer_reminders import reminder_loop
from bot.services.subscription_reminders import subscription_reminder_loop
from bot.instance_lock import InstanceLock
from config import config

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    log_dir = Path("outputs")
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        file_handler = RotatingFileHandler(
            log_dir / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    if not any(type(handler) is logging.StreamHandler for handler in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args and context.args[0].strip().lower() == "reklama":
        await ads_section(update, context)
        return
    await main_menu_command(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Forbidden):
        user = getattr(update, "effective_user", None)
        if user:
            set_bot_user_active(user.id, False)
        logger.info("Telegram xabari yuborilmadi: foydalanuvchi botni bloklagan")
        return
    logger.error("Telegram update xatosi", exc_info=context.error)


async def start_reminder_service(application: Application) -> None:
    stop_event = asyncio.Event()
    reminder_task = asyncio.create_task(
        reminder_loop(application.bot, stop_event),
        name="prayer-reminders",
    )
    daily_dua_task = asyncio.create_task(
        daily_dua_loop(application.bot, stop_event),
        name="daily-dua",
    )
    subscription_task = asyncio.create_task(
        subscription_reminder_loop(application.bot, stop_event),
        name="subscription-reminders",
    )
    application.bot_data["prayer_reminder_stop"] = stop_event
    application.bot_data["prayer_reminder_task"] = reminder_task
    application.bot_data["daily_dua_task"] = daily_dua_task
    application.bot_data["subscription_reminder_task"] = subscription_task


async def stop_reminder_service(application: Application) -> None:
    stop_event = application.bot_data.get("prayer_reminder_stop")
    tasks = [
        application.bot_data.get("prayer_reminder_task"),
        application.bot_data.get("daily_dua_task"),
        application.bot_data.get("subscription_reminder_task"),
    ]
    if stop_event:
        stop_event.set()
    for task in tasks:
        if task:
            await task


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. .env faylini tekshiring.")
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(start_reminder_service)
        .post_shutdown(stop_reminder_service)
        .build()
    )
    app.add_handler(user_tracker_handler(), group=-1)
    app.add_handler(CommandHandler("start", start), group=0)
    app.add_handler(admin_handler(), group=0)
    for handler in daily_dua_admin_handlers():
        app.add_handler(handler, group=0)
    for handler in driver_handlers():
        app.add_handler(handler, group=0)
    app.add_handler(driver_profile_conversation(), group=0)
    for handler in auto_services_handlers():
        app.add_handler(handler, group=0)
    for handler in content_handlers():
        app.add_handler(handler, group=0)
    for handler in service_handlers():
        app.add_handler(handler, group=0)
    for handler in memory_handlers():
        app.add_handler(handler, group=0)
    app.add_handler(search_handler(), group=0)
    app.add_handler(taxi_conversation(), group=0)
    app.add_handler(claim_handler(), group=0)
    for handler in rating_handlers():
        app.add_handler(handler, group=0)
    app.add_handler(menu_handler(), group=0)
    app.add_handler(prayer_handler(), group=1)
    app.add_handler(next_prayer_handler(), group=1)
    app.add_handler(dhikr_handler(), group=1)
    app.add_handler(dhikr_callback_handler(), group=1)
    app.add_handler(reminders_handler(), group=1)
    app.add_handler(reminder_toggle_handler(), group=1)
    app.add_handler(daily_dua_handler(), group=1)
    for handler in ads_handlers():
        app.add_handler(handler, group=1)
    app.add_handler(contact_handler(), group=1)
    app.add_handler(about_handler(), group=1)
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    """Initialize storage and let PTB own the polling event-loop lifecycle.

    PTB 22.7 contains the Python 3.14 event-loop compatibility fix. Do not wrap
    run_polling() in asyncio.run(): run_polling manages startup and shutdown.
    """
    configure_logging()
    with InstanceLock(Path("data/bot.lock")):
        init_db()
        logger.info("Bot ishga tushmoqda...")
        application = build_application()
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
