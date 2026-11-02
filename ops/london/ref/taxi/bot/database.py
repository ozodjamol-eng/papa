import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from config import config


def _connect() -> sqlite3.Connection:
    path = Path(config.DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(_connect()) as db:
        with db:
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            username TEXT, taxi_type TEXT NOT NULL, origin TEXT NOT NULL,
            destination TEXT NOT NULL, passengers INTEGER NOT NULL, phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new', driver_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            order_columns = {row[1] for row in db.execute("PRAGMA table_info(taxi_orders)")}
            if "route" not in order_columns:
                db.execute("ALTER TABLE taxi_orders ADD COLUMN route TEXT")
            if "route_key" not in order_columns:
                db.execute("ALTER TABLE taxi_orders ADD COLUMN route_key TEXT NOT NULL DEFAULT 'local'")
            if "accepted_at" not in order_columns:
                db.execute("ALTER TABLE taxi_orders ADD COLUMN accepted_at TEXT")
            if "completed_at" not in order_columns:
                db.execute("ALTER TABLE taxi_orders ADD COLUMN completed_at TEXT")
            if "cancelled_at" not in order_columns:
                db.execute("ALTER TABLE taxi_orders ADD COLUMN cancelled_at TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_routes (
            route_key TEXT PRIMARY KEY, label TEXT NOT NULL, sort_order INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.executemany("""INSERT OR IGNORE INTO taxi_routes(route_key,label,sort_order)
            VALUES (?,?,?)""", (
                ("local", "Хўжаобод ичида", 10), ("andijon", "Андижон", 20),
                ("tashkent", "Тошкент", 30), ("other", "Бошқа йўналиш", 40),
            ))
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_driver_routes (
            driver_id INTEGER NOT NULL, route_key TEXT NOT NULL,
            PRIMARY KEY(driver_id, route_key),
            FOREIGN KEY(driver_id) REFERENCES taxi_drivers(user_id),
            FOREIGN KEY(route_key) REFERENCES taxi_routes(route_key))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_taxi_orders_route_status ON taxi_orders(route, status, id DESC)")
            db.execute("""CREATE TABLE IF NOT EXISTS prayer_reminders (
            user_id INTEGER NOT NULL, prayer_key TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, prayer_key))""")
            db.execute("""CREATE TABLE IF NOT EXISTS prayer_notifications (
            user_id INTEGER NOT NULL, prayer_key TEXT NOT NULL,
            prayer_date TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, prayer_key, prayer_date))""")
            db.execute("""CREATE TABLE IF NOT EXISTS bot_users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS daily_dua_deliveries (
            user_id INTEGER NOT NULL, delivery_date TEXT NOT NULL,
            dua_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'reserved',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, delivery_date))""")
            db.execute("""CREATE TABLE IF NOT EXISTS daily_dua_groups (
            chat_id INTEGER PRIMARY KEY, title TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            added_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS daily_dua_group_deliveries (
            chat_id INTEGER NOT NULL, delivery_date TEXT NOT NULL,
            dua_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'reserved',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, delivery_date))""")
            db.execute("""CREATE TABLE IF NOT EXISTS daily_dua_stats (
            delivery_date TEXT PRIMARY KEY,
            user_sent INTEGER NOT NULL DEFAULT 0,
            group_sent INTEGER NOT NULL DEFAULT 0,
            user_errors INTEGER NOT NULL DEFAULT 0,
            group_errors INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_drivers (
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
            registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            driver_columns = {row[1] for row in db.execute("PRAGMA table_info(taxi_drivers)")}
            if "subscription_starts_at" not in driver_columns:
                db.execute("ALTER TABLE taxi_drivers ADD COLUMN subscription_starts_at TEXT")
            if "subscription_expires_at" not in driver_columns:
                db.execute("ALTER TABLE taxi_drivers ADD COLUMN subscription_expires_at TEXT")
            if "is_suspended" not in driver_columns:
                db.execute("ALTER TABLE taxi_drivers ADD COLUMN is_suspended INTEGER NOT NULL DEFAULT 0")
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, driver_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, kind TEXT NOT NULL, order_id INTEGER,
            admin_id INTEGER, note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(driver_id) REFERENCES taxi_drivers(user_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            amount INTEGER NOT NULL CHECK (amount >= 5000 AND amount <= 10000000),
            receipt_file_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','approved','rejected')),
            reviewer_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            FOREIGN KEY(driver_id) REFERENCES taxi_drivers(user_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_taxi_topups_driver ON taxi_topups(driver_id, status, id DESC)")
            db.execute("""CREATE TABLE IF NOT EXISTS auto_driver_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            capacity TEXT NOT NULL,
            service_area TEXT NOT NULL,
            plate TEXT NOT NULL,
            public_phone INTEGER NOT NULL DEFAULT 0 CHECK (public_phone IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'payment_pending'
                CHECK (status IN ('payment_pending','active','rejected','suspended')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, category),
            FOREIGN KEY(user_id) REFERENCES taxi_drivers(user_id))""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_auto_driver_profiles_catalog
            ON auto_driver_profiles(category, status, user_id)""")
            db.execute("""CREATE TABLE IF NOT EXISTS subscription_reminders (
            subject_type TEXT NOT NULL CHECK (subject_type IN ('driver','ad')),
            subject_id INTEGER NOT NULL,
            reminder_date TEXT NOT NULL,
            period TEXT NOT NULL CHECK (period IN ('morning','evening')),
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(subject_type, subject_id, reminder_date, period))""")
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL, driver_id INTEGER NOT NULL,
            stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5), reason TEXT,
            complaint_status TEXT CHECK(complaint_status IN ('pending','warned','dismissed','blocked')),
            reviewed_by INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            FOREIGN KEY(order_id) REFERENCES taxi_orders(id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS taxi_driver_warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, driver_id INTEGER NOT NULL,
            rating_id INTEGER NOT NULL UNIQUE, reason TEXT NOT NULL, admin_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS admin_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            details TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new'
                CHECK (status IN ('new','planned','in_progress','testing','ready_for_approval',
                                  'approved','deployed','verified','done','blocked','rejected',
                                  'failed','rolled_back','cancelled')),
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS admin_task_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES admin_tasks(id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_admin_tasks_status ON admin_tasks(status, id DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_admin_task_events_task ON admin_task_events(task_id, id)")
            admin_task_columns = {row[1] for row in db.execute("PRAGMA table_info(admin_tasks)")}
            if "agent_task_id" not in admin_task_columns:
                db.execute("ALTER TABLE admin_tasks ADD COLUMN agent_task_id INTEGER")
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','in_progress','completed','failed','ready_for_approval','cancelled')),
            report TEXT,
            source_admin_task_id INTEGER UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            task_columns = {row[1] for row in db.execute("PRAGMA table_info(tasks)")}
            if "source_admin_task_id" not in task_columns:
                db.execute("ALTER TABLE tasks ADD COLUMN source_admin_task_id INTEGER")
            if "target_worker" not in task_columns:
                db.execute("ALTER TABLE tasks ADD COLUMN target_worker TEXT NOT NULL DEFAULT 'windows'")
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_id ON tasks(status, id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker_status_id ON tasks(target_worker, status, id)")
            db.execute("""CREATE TABLE IF NOT EXISTS content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL CHECK (category IN ('service', 'ad', 'property', 'useful')),
            text TEXT NOT NULL, author_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'approved', 'rejected', 'published')),
            reviewer_id INTEGER, channel_message_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT, published_at TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS service_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS ad_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'payment_pending'
                CHECK (status IN ('payment_pending','review','active','rejected','expired','closed')),
            starts_at TEXT, expires_at TEXT, reviewer_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS ad_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            amount INTEGER NOT NULL CHECK (amount > 0),
            months INTEGER NOT NULL DEFAULT 1 CHECK (months > 0),
            receipt_file_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','approved','rejected')),
            reviewer_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            FOREIGN KEY(listing_id) REFERENCES ad_listings(id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_ad_listings_owner ON ad_listings(owner_id, id DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_ad_listings_active ON ad_listings(category, status, expires_at)")
            ad_columns = {row[1] for row in db.execute("PRAGMA table_info(ad_listings)")}
            if "price_text" not in ad_columns:
                db.execute("ALTER TABLE ad_listings ADD COLUMN price_text TEXT")
            if "work_hours" not in ad_columns:
                db.execute("ALTER TABLE ad_listings ADD COLUMN work_hours TEXT")
            if "latitude" not in ad_columns:
                db.execute("ALTER TABLE ad_listings ADD COLUMN latitude REAL")
            if "longitude" not in ad_columns:
                db.execute("ALTER TABLE ad_listings ADD COLUMN longitude REAL")
            if "verified" not in ad_columns:
                db.execute("ALTER TABLE ad_listings ADD COLUMN verified INTEGER NOT NULL DEFAULT 0")
            db.execute("""CREATE TABLE IF NOT EXISTS ad_listing_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(listing_id, file_id),
            FOREIGN KEY(listing_id) REFERENCES ad_listings(id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_ad_media_listing ON ad_listing_media(listing_id, sort_order, id)")
            db.execute("""CREATE TABLE IF NOT EXISTS memory_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            death_date TEXT NOT NULL,
            memory_text TEXT NOT NULL,
            photo_file_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','publishing','published','rejected')),
            reviewer_id INTEGER,
            channel_message_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            published_at TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_submissions(status, id)")
            content_schema = db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='content_items'"
            ).fetchone()
            if content_schema and "'news'" in str(content_schema[0]):
                db.execute("ALTER TABLE content_items RENAME TO content_items_legacy")
                db.execute("""CREATE TABLE content_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL CHECK (category IN ('service', 'ad', 'property', 'useful')),
                text TEXT NOT NULL, author_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'approved', 'rejected', 'published')),
                reviewer_id INTEGER, channel_message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT, published_at TEXT)""")
                db.execute("""INSERT INTO content_items
                (id, category, text, author_id, status, reviewer_id, channel_message_id,
                 created_at, reviewed_at, published_at)
                SELECT id, CASE WHEN category='news' THEN 'useful' ELSE category END,
                text, author_id, status, reviewer_id, channel_message_id,
                created_at, reviewed_at, published_at FROM content_items_legacy""")
                db.execute("DROP TABLE content_items_legacy")
            db.execute("""INSERT OR IGNORE INTO bot_users (user_id, username)
            SELECT DISTINCT user_id, username FROM taxi_orders""")
            db.execute("""INSERT OR IGNORE INTO bot_users (user_id)
            SELECT DISTINCT user_id FROM prayer_reminders""")


def create_memory_submission(owner_id: int, full_name: str, birth_date: str,
                             death_date: str, memory_text: str, photo_file_id: str) -> int:
    values = (full_name.strip(), birth_date.strip(), death_date.strip(), memory_text.strip(), photo_file_id.strip())
    if not owner_id or any(not value for value in values):
        raise ValueError("Хотира маълумотлари тўлиқ бўлиши керак")
    with closing(_connect()) as db:
        with db:
            pending = db.execute(
                "SELECT COUNT(*) FROM memory_submissions WHERE owner_id=? AND status IN ('pending','publishing')",
                (owner_id,),
            ).fetchone()[0]
            if pending >= 3:
                raise ValueError("Текширувдаги аризалар сони чекланган")
            cursor = db.execute(
                """INSERT INTO memory_submissions
                (owner_id,full_name,birth_date,death_date,memory_text,photo_file_id)
                VALUES (?,?,?,?,?,?)""",
                (owner_id, *values),
            )
            return int(cursor.lastrowid)


def memory_submission(submission_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM memory_submissions WHERE id=?", (submission_id,)).fetchone()


def reserve_memory_publication(submission_id: int, reviewer_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        with db:
            changed = db.execute(
                """UPDATE memory_submissions SET status='publishing', reviewer_id=?,
                reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'""",
                (reviewer_id, submission_id),
            ).rowcount
            return db.execute("SELECT * FROM memory_submissions WHERE id=?", (submission_id,)).fetchone() if changed else None


def finish_memory_publication(submission_id: int, channel_message_id: int) -> bool:
    with closing(_connect()) as db:
        with db:
            return bool(db.execute(
                """UPDATE memory_submissions SET status='published', channel_message_id=?,
                published_at=CURRENT_TIMESTAMP WHERE id=? AND status='publishing'""",
                (channel_message_id, submission_id),
            ).rowcount)


def release_memory_publication(submission_id: int) -> bool:
    with closing(_connect()) as db:
        with db:
            return bool(db.execute(
                "UPDATE memory_submissions SET status='pending', reviewer_id=NULL WHERE id=? AND status='publishing'",
                (submission_id,),
            ).rowcount)


def reject_memory_submission(submission_id: int, reviewer_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        with db:
            changed = db.execute(
                """UPDATE memory_submissions SET status='rejected', reviewer_id=?,
                reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'""",
                (reviewer_id, submission_id),
            ).rowcount
            return db.execute("SELECT * FROM memory_submissions WHERE id=?", (submission_id,)).fetchone() if changed else None


def system_stats() -> dict[str, int | str]:
    with closing(_connect()) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        return {
            "integrity": str(integrity),
            "users": int(db.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]),
            "active_users": int(db.execute("SELECT COUNT(*) FROM bot_users WHERE is_active=1").fetchone()[0]),
            "taxi_orders": int(db.execute("SELECT COUNT(*) FROM taxi_orders").fetchone()[0]),
            "new_taxi_orders": int(db.execute("SELECT COUNT(*) FROM taxi_orders WHERE status='new'").fetchone()[0]),
            "content_drafts": int(db.execute("SELECT COUNT(*) FROM content_items WHERE status='draft'").fetchone()[0]),
            "active_services": int(db.execute("SELECT COUNT(*) FROM service_listings WHERE is_active=1").fetchone()[0]),
            "active_ads": int(db.execute("SELECT COUNT(*) FROM ad_listings WHERE status='active' AND expires_at > CURRENT_TIMESTAMP").fetchone()[0]),
            "pending_ads": int(db.execute("SELECT COUNT(*) FROM ad_payments WHERE status='pending'").fetchone()[0]),
            "pending_taxi_topups": int(db.execute("SELECT COUNT(*) FROM taxi_topups WHERE status='pending'").fetchone()[0]),
        }


def create_ad_listing(owner_id: int, category: str, title: str, description: str,
                      address: str, phone: str, price_text: str = "",
                      work_hours: str = "", latitude: float | None = None,
                      longitude: float | None = None,
                      photo_file_ids: list[str] | None = None) -> int:
    values = [category.strip(), title.strip(), description.strip(), address.strip(), phone.strip()]
    if any(not value for value in values):
        raise ValueError("required ad field is empty")
    with closing(_connect()) as db:
        with db:
            pending = db.execute(
                "SELECT COUNT(*) FROM ad_listings WHERE owner_id=? AND status IN ('payment_pending','review')",
                (owner_id,),
            ).fetchone()[0]
            if pending >= 3:
                raise ValueError("too many pending listings")
            cursor = db.execute(
                """INSERT INTO ad_listings
                (owner_id, category, title, description, address, phone,
                 price_text, work_hours, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (owner_id, *values, price_text.strip(), work_hours.strip(), latitude, longitude),
            )
            listing_id = int(cursor.lastrowid)
            for index, file_id in enumerate((photo_file_ids or [])[:5]):
                if file_id.strip():
                    db.execute(
                        "INSERT OR IGNORE INTO ad_listing_media (listing_id,file_id,sort_order) VALUES (?,?,?)",
                        (listing_id, file_id.strip(), index),
                    )
            return listing_id


def ad_listing(listing_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM ad_listings WHERE id=?", (listing_id,)).fetchone()


def user_ad_listings(owner_id: int, limit: int = 20) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            "SELECT * FROM ad_listings WHERE owner_id=? ORDER BY id DESC LIMIT ?", (owner_id, limit)
        ))


def active_ad_listings(category: str, limit: int = 20) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        with db:
            db.execute("UPDATE ad_listings SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE status='active' AND expires_at <= CURRENT_TIMESTAMP")
            return list(db.execute(
                """SELECT a.*,
                (SELECT file_id FROM ad_listing_media m WHERE m.listing_id=a.id ORDER BY sort_order,id LIMIT 1) AS photo_file_id
                FROM ad_listings a WHERE category=? AND status='active'
                AND expires_at > CURRENT_TIMESTAMP ORDER BY id DESC LIMIT ?""", (category, limit)
            ))


def search_active_ads(term: str, limit: int = 10) -> list[sqlite3.Row]:
    cleaned = " ".join(term.split()).strip()[:80]
    if len(cleaned) < 2:
        return []
    escaped = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    with closing(_connect()) as db:
        with db:
            db.execute("UPDATE ad_listings SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE status='active' AND expires_at <= CURRENT_TIMESTAMP")
            return list(db.execute(
                """SELECT a.*,
                (SELECT file_id FROM ad_listing_media m WHERE m.listing_id=a.id ORDER BY sort_order,id LIMIT 1) AS photo_file_id
                FROM ad_listings a WHERE a.status='active' AND a.expires_at>CURRENT_TIMESTAMP
                AND (a.title LIKE ? ESCAPE '\\' OR a.description LIKE ? ESCAPE '\\'
                     OR a.address LIKE ? ESCAPE '\\' OR a.price_text LIKE ? ESCAPE '\\')
                ORDER BY a.verified DESC, a.id DESC LIMIT ?""",
                (pattern, pattern, pattern, pattern, limit),
            ))


def ad_control_stats() -> dict[str, int]:
    with closing(_connect()) as db:
        row = db.execute("""SELECT COUNT(*),
            SUM(CASE WHEN status='active' AND expires_at>CURRENT_TIMESTAMP THEN 1 ELSE 0 END),
            SUM(CASE WHEN status IN ('payment_pending','review') THEN 1 ELSE 0 END),
            SUM(CASE WHEN status='expired' OR (status='active' AND expires_at<=CURRENT_TIMESTAMP) THEN 1 ELSE 0 END),
            SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status='active' AND date(expires_at) BETWEEN date('now') AND date('now','+2 days') THEN 1 ELSE 0 END)
            FROM ad_listings""").fetchone()
        return {"total": int(row[0]), "active": int(row[1] or 0), "pending": int(row[2] or 0),
                "expired": int(row[3] or 0), "rejected": int(row[4] or 0), "expiring": int(row[5] or 0)}


def ads_by_control_status(status: str, limit: int = 30) -> list[sqlite3.Row]:
    conditions = {"active": "status='active' AND expires_at>CURRENT_TIMESTAMP",
                  "pending": "status IN ('payment_pending','review')",
                  "expired": "status='expired' OR (status='active' AND expires_at<=CURRENT_TIMESTAMP)",
                  "rejected": "status='rejected'",
                  "expiring": "status='active' AND date(expires_at) BETWEEN date('now') AND date('now','+2 days')"}
    if status not in conditions: raise ValueError("invalid ad status")
    with closing(_connect()) as db:
        return list(db.execute(f"SELECT id,owner_id,title,expires_at FROM ad_listings WHERE {conditions[status]} ORDER BY id DESC LIMIT ?", (limit,)))


def add_ad_payment(listing_id: int, owner_id: int, amount: int, receipt_file_id: str) -> int:
    with closing(_connect()) as db:
        with db:
            row = db.execute("SELECT owner_id, status FROM ad_listings WHERE id=?", (listing_id,)).fetchone()
            if not row or int(row["owner_id"]) != owner_id or row["status"] == "closed":
                raise ValueError("listing unavailable")
            pending = db.execute(
                "SELECT 1 FROM ad_payments WHERE listing_id=? AND status='pending' LIMIT 1",
                (listing_id,),
            ).fetchone()
            if pending:
                raise ValueError("payment already pending")
            if db.execute("SELECT 1 FROM taxi_topups WHERE receipt_file_id=?", (receipt_file_id,)).fetchone():
                raise sqlite3.IntegrityError("receipt already used")
            cursor = db.execute(
                """INSERT INTO ad_payments (listing_id, owner_id, amount, receipt_file_id)
                VALUES (?, ?, ?, ?)""", (listing_id, owner_id, amount, receipt_file_id)
            )
            db.execute("""UPDATE ad_listings SET
                status=CASE WHEN status='active' AND expires_at > CURRENT_TIMESTAMP THEN 'active' ELSE 'review' END,
                updated_at=CURRENT_TIMESTAMP WHERE id=?""", (listing_id,))
            return int(cursor.lastrowid)


def ad_payment(payment_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM ad_payments WHERE id=?", (payment_id,)).fetchone()


def review_ad_payment(payment_id: int, reviewer_id: int, approved: bool) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            payment = db.execute("SELECT * FROM ad_payments WHERE id=? AND status='pending'", (payment_id,)).fetchone()
            if not payment:
                db.rollback()
                return None
            listing = db.execute("SELECT * FROM ad_listings WHERE id=?", (payment["listing_id"],)).fetchone()
            status = "approved" if approved else "rejected"
            db.execute("UPDATE ad_payments SET status=?, reviewer_id=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?", (status, reviewer_id, payment_id))
            if approved:
                db.execute("""UPDATE ad_listings SET status='active', reviewer_id=?,
                    starts_at=COALESCE(starts_at, CURRENT_TIMESTAMP),
                    expires_at=datetime(CASE WHEN expires_at > CURRENT_TIMESTAMP THEN expires_at ELSE CURRENT_TIMESTAMP END, '+30 days'),
                    updated_at=CURRENT_TIMESTAMP WHERE id=?""", (reviewer_id, payment["listing_id"]))
            else:
                db.execute("""UPDATE ad_listings SET
                    status=CASE WHEN expires_at > CURRENT_TIMESTAMP THEN 'active' ELSE 'rejected' END,
                    reviewer_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (reviewer_id, payment["listing_id"]))
            result = db.execute("SELECT * FROM ad_listings WHERE id=?", (payment["listing_id"],)).fetchone()
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise


def create_content(category: str, text: str, author_id: int) -> int:
    if category not in {"service", "ad", "property", "useful"}:
        raise ValueError("unsupported content category")
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("content text is empty")
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                "INSERT INTO content_items (category, text, author_id) VALUES (?, ?, ?)",
                (category, clean_text, author_id),
            )
            return int(cursor.lastrowid)


def add_service_listing(
    category: str,
    title: str,
    description: str,
    phone: str,
    address: str | None,
    created_by: int,
) -> int:
    values = [category.strip(), title.strip(), description.strip(), phone.strip()]
    if any(not value for value in values):
        raise ValueError("required service field is empty")
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT INTO service_listings
                (category, title, description, phone, address, created_by)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (values[0], values[1], values[2], values[3], (address or "").strip() or None, created_by),
            )
            return int(cursor.lastrowid)


def service_categories() -> list[str]:
    with closing(_connect()) as db:
        return [str(row[0]) for row in db.execute(
            "SELECT DISTINCT category FROM service_listings WHERE is_active=1 ORDER BY category"
        )]


def services_by_category(category: str, limit: int = 20) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            """SELECT * FROM service_listings
            WHERE category=? AND is_active=1 ORDER BY id DESC LIMIT ?""",
            (category, limit),
        ))


def all_services(limit: int = 50) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            "SELECT * FROM service_listings ORDER BY is_active DESC, id DESC LIMIT ?", (limit,)
        ))


def deactivate_service(item_id: int) -> bool:
    with closing(_connect()) as db:
        with db:
            return db.execute(
                """UPDATE service_listings SET is_active=0, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND is_active=1""",
                (item_id,),
            ).rowcount == 1


def content_queue(limit: int = 20) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            "SELECT * FROM content_items WHERE status IN ('draft', 'approved') ORDER BY id LIMIT ?",
            (limit,),
        ))


def content_item(item_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone()


def review_content(item_id: int, reviewer_id: int, approved: bool) -> bool:
    status = "approved" if approved else "rejected"
    with closing(_connect()) as db:
        with db:
            return db.execute(
                """UPDATE content_items SET status=?, reviewer_id=?, reviewed_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='draft'""",
                (status, reviewer_id, item_id),
            ).rowcount == 1


def mark_content_published(item_id: int, channel_message_id: int) -> bool:
    with closing(_connect()) as db:
        with db:
            return db.execute(
                """UPDATE content_items SET status='published', channel_message_id=?,
                published_at=CURRENT_TIMESTAMP WHERE id=? AND status='approved'""",
                (channel_message_id, item_id),
            ).rowcount == 1


def create_order(data: dict[str, Any]) -> int:
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT INTO taxi_orders
                (user_id, username, taxi_type, route, origin, destination, passengers, phone, route_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (data["user_id"], data.get("username"), data["taxi_type"],
                 data.get("route", data["taxi_type"]), data["origin"], data["destination"],
                 data.get("passengers", 1), data["phone"], data.get("route_key", "local")),
            )
            return int(cursor.lastrowid)


def taxi_routes() -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            "SELECT route_key,label,sort_order FROM taxi_routes WHERE is_active=1 ORDER BY sort_order"
        ))


def taxi_route_info(route_key: str) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("""SELECT route_key,label,sort_order FROM taxi_routes
            WHERE route_key=? AND is_active=1""", (route_key,)).fetchone()


def customer_taxi_orders(user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute("""SELECT o.*, COALESCE(r.label,o.taxi_type) AS route_label
            FROM taxi_orders o LEFT JOIN taxi_routes r ON r.route_key=o.route_key
            WHERE o.user_id=? ORDER BY o.id DESC LIMIT ?""", (user_id, limit)))


def driver_taxi_orders(driver_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute("""SELECT o.*, COALESCE(r.label,o.taxi_type) AS route_label
            FROM taxi_orders o LEFT JOIN taxi_routes r ON r.route_key=o.route_key
            WHERE o.driver_id=? ORDER BY o.id DESC LIMIT ?""", (driver_id, limit)))


def driver_route_keys(driver_id: int) -> set[str]:
    with closing(_connect()) as db:
        return {str(row[0]) for row in db.execute(
            "SELECT route_key FROM taxi_driver_routes WHERE driver_id=?", (driver_id,)
        )}


def toggle_driver_route(driver_id: int, route_key: str) -> bool:
    with closing(_connect()) as db:
        with db:
            if not db.execute("SELECT 1 FROM taxi_routes WHERE route_key=? AND is_active=1", (route_key,)).fetchone():
                raise ValueError("unknown route")
            exists = db.execute("""SELECT 1 FROM taxi_driver_routes
                WHERE driver_id=? AND route_key=?""", (driver_id, route_key)).fetchone()
            if exists:
                db.execute("DELETE FROM taxi_driver_routes WHERE driver_id=? AND route_key=?", (driver_id, route_key))
                return False
            db.execute("INSERT INTO taxi_driver_routes(driver_id,route_key) VALUES (?,?)", (driver_id, route_key))
            return True


def finish_taxi_order(order_id: int, driver_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        with db:
            changed = db.execute("""UPDATE taxi_orders SET status='completed', completed_at=CURRENT_TIMESTAMP
                WHERE id=? AND driver_id=? AND status='accepted'""", (order_id, driver_id)).rowcount
            return db.execute("SELECT * FROM taxi_orders WHERE id=?", (order_id,)).fetchone() if changed else None


def cancel_taxi_order(order_id: int, user_id: int) -> bool:
    with closing(_connect()) as db:
        with db:
            return db.execute("""UPDATE taxi_orders SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP
                WHERE id=? AND user_id=? AND status='new'""", (order_id, user_id)).rowcount == 1


def create_agent_task(
    task_type: str,
    payload: str,
    target_worker: str = "windows",
) -> int:
    clean_type = task_type.strip()
    clean_payload = payload.strip()
    clean_worker = target_worker.strip().lower()
    if not clean_type or not clean_payload:
        raise ValueError("task type and payload are required")
    if clean_worker not in {"windows", "nexus"}:
        raise ValueError("unsupported target worker")
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT INTO tasks (task_type, payload, target_worker)
                VALUES (?, ?, ?)""",
                (clean_type, clean_payload, clean_worker),
            )
            return int(cursor.lastrowid)


def claim_next_agent_task(target_worker: str = "windows") -> sqlite3.Row | None:
    clean_worker = target_worker.strip().lower()
    if clean_worker not in {"windows", "nexus"}:
        raise ValueError("unsupported target worker")
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            task = db.execute(
                """SELECT * FROM tasks
                WHERE status='pending' AND target_worker=?
                ORDER BY id LIMIT 1""",
                (clean_worker,),
            ).fetchone()
            if not task:
                db.rollback()
                return None
            changed = db.execute(
                """UPDATE tasks SET status='in_progress', updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='pending'""",
                (task["id"],),
            ).rowcount
            if not changed:
                db.rollback()
                return None
            claimed = db.execute("SELECT * FROM tasks WHERE id=?", (task["id"],)).fetchone()
            db.commit()
            return claimed
        except Exception:
            db.rollback()
            raise


def agent_task(task_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()


def report_agent_task(task_id: int, status: str, report: str) -> sqlite3.Row | None:
    if status not in {"completed", "failed", "ready_for_approval"}:
        raise ValueError("invalid task report status")
    clean_report = report.strip()
    if not clean_report:
        raise ValueError("task report is required")
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            changed = db.execute(
                """UPDATE tasks SET status=?, report=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='in_progress'""",
                (status, clean_report, task_id),
            ).rowcount
            if not changed:
                db.rollback()
                return None
            task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            source_admin_task_id = task["source_admin_task_id"]
            if source_admin_task_id is not None:
                admin_status = "done" if status == "completed" else status
                old_status = db.execute(
                    "SELECT status FROM admin_tasks WHERE id=?",
                    (source_admin_task_id,),
                ).fetchone()
                if old_status:
                    db.execute(
                        """UPDATE admin_tasks SET status=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?""",
                        (admin_status, source_admin_task_id),
                    )
                    db.execute(
                        """INSERT INTO admin_task_events
                        (task_id, actor_id, old_status, new_status, note)
                        VALUES (?, 0, ?, ?, ?)""",
                        (
                            source_admin_task_id,
                            old_status["status"],
                            admin_status,
                            clean_report[:1000],
                        ),
                    )
            db.commit()
            return task
        except Exception:
            db.rollback()
            raise


def user_taxi_orders(user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            """SELECT * FROM taxi_orders WHERE user_id=? ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ))


def register_driver(user_id: int, username: str | None, full_name: str | None) -> sqlite3.Row:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO taxi_drivers (user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username, full_name=excluded.full_name,
                    is_active=1, updated_at=CURRENT_TIMESTAMP""",
                (user_id, username, full_name),
            )
            return db.execute("SELECT * FROM taxi_drivers WHERE user_id=?", (user_id,)).fetchone()


def driver_info(user_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM taxi_drivers WHERE user_id=?", (user_id,)).fetchone()


def save_auto_driver_profile(
    user_id: int, category: str, phone: str, vehicle: str, capacity: str,
    service_area: str, plate: str, public_phone: bool,
) -> sqlite3.Row:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO auto_driver_profiles
                (user_id, category, phone, vehicle, capacity, service_area, plate, public_phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, category) DO UPDATE SET
                    phone=excluded.phone, vehicle=excluded.vehicle,
                    capacity=excluded.capacity, service_area=excluded.service_area,
                    plate=excluded.plate, public_phone=excluded.public_phone,
                    status='payment_pending', updated_at=CURRENT_TIMESTAMP""",
                (user_id, category, phone, vehicle, capacity, service_area, plate, int(public_phone)),
            )
            return db.execute(
                "SELECT * FROM auto_driver_profiles WHERE user_id=? AND category=?",
                (user_id, category),
            ).fetchone()


def active_auto_driver_profiles(categories: tuple[str, ...], limit: int = 30) -> list[sqlite3.Row]:
    if not categories:
        return []
    placeholders = ",".join("?" for _ in categories)
    with closing(_connect()) as db:
        return list(db.execute(
            f"""SELECT p.*, d.full_name, d.username
            FROM auto_driver_profiles p
            JOIN taxi_drivers d ON d.user_id=p.user_id
            WHERE p.category IN ({placeholders}) AND p.status='active'
              AND p.public_phone=1 AND d.is_active=1 AND d.is_suspended=0
              AND d.subscription_expires_at > CURRENT_TIMESTAMP
            ORDER BY p.updated_at DESC LIMIT ?""",
            (*categories, limit),
        ))


def auto_driver_profiles(user_id: int) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            "SELECT * FROM auto_driver_profiles WHERE user_id=? ORDER BY id", (user_id,)
        ))


def driver_rating(driver_id: int) -> dict[str, float | int]:
    with closing(_connect()) as db:
        row = db.execute("SELECT COALESCE(AVG(stars),0), COUNT(*) FROM taxi_ratings WHERE driver_id=?", (driver_id,)).fetchone()
        warnings = db.execute("SELECT COUNT(*) FROM taxi_driver_warnings WHERE driver_id=? AND created_at >= datetime('now','-90 days')", (driver_id,)).fetchone()[0]
        return {"average": round(float(row[0]), 2), "count": int(row[1]), "warnings": int(warnings)}


def add_taxi_rating(order_id: int, customer_id: int, stars: int) -> sqlite3.Row:
    if stars not in range(1, 6):
        raise ValueError("invalid stars")
    with closing(_connect()) as db:
        with db:
            order = db.execute("SELECT user_id, driver_id, status FROM taxi_orders WHERE id=?", (order_id,)).fetchone()
            if not order or int(order["user_id"]) != customer_id or order["status"] != "accepted" or not order["driver_id"]:
                raise ValueError("rating unavailable")
            cursor = db.execute("""INSERT INTO taxi_ratings
                (order_id, customer_id, driver_id, stars, complaint_status)
                VALUES (?, ?, ?, ?, ?)""", (order_id, customer_id, order["driver_id"], stars, "pending" if stars <= 2 else None))
            return db.execute("SELECT * FROM taxi_ratings WHERE id=?", (cursor.lastrowid,)).fetchone()


def set_rating_reason(rating_id: int, customer_id: int, reason: str) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        with db:
            db.execute("UPDATE taxi_ratings SET reason=? WHERE id=? AND customer_id=? AND complaint_status='pending'", (reason, rating_id, customer_id))
            return db.execute("SELECT * FROM taxi_ratings WHERE id=? AND customer_id=?", (rating_id, customer_id)).fetchone()


def review_driver_complaint(rating_id: int, admin_id: int, action: str) -> tuple[sqlite3.Row, int] | None:
    if action not in {"warn", "dismiss", "block"}:
        raise ValueError("invalid action")
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            rating = db.execute("SELECT * FROM taxi_ratings WHERE id=? AND complaint_status='pending' AND reason IS NOT NULL", (rating_id,)).fetchone()
            if not rating:
                db.rollback(); return None
            status = {"warn": "warned", "dismiss": "dismissed", "block": "blocked"}[action]
            db.execute("UPDATE taxi_ratings SET complaint_status=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?", (status, admin_id, rating_id))
            if action in {"warn", "block"}:
                db.execute("INSERT INTO taxi_driver_warnings(driver_id,rating_id,reason,admin_id) VALUES(?,?,?,?)", (rating["driver_id"], rating_id, rating["reason"], admin_id))
            warnings = int(db.execute("SELECT COUNT(*) FROM taxi_driver_warnings WHERE driver_id=? AND created_at >= datetime('now','-90 days')", (rating["driver_id"],)).fetchone()[0])
            if action == "block" or warnings >= 3:
                db.execute("UPDATE taxi_drivers SET is_suspended=1, updated_at=CURRENT_TIMESTAMP WHERE user_id=?", (rating["driver_id"],))
            db.commit(); return rating, warnings
        except Exception:
            db.rollback(); raise


def add_taxi_topup(driver_id: int, amount: int, receipt_file_id: str) -> int:
    if amount != config.TAXI_MONTHLY_PRICE:
        raise ValueError("topup amount out of range")
    with closing(_connect()) as db:
        with db:
            if not db.execute(
                "SELECT 1 FROM taxi_drivers WHERE user_id=? AND is_active=1", (driver_id,)
            ).fetchone():
                raise ValueError("driver unavailable")
            if db.execute(
                "SELECT 1 FROM taxi_topups WHERE driver_id=? AND status='pending' LIMIT 1", (driver_id,)
            ).fetchone():
                raise ValueError("topup already pending")
            if db.execute("SELECT 1 FROM ad_payments WHERE receipt_file_id=?", (receipt_file_id,)).fetchone():
                raise sqlite3.IntegrityError("receipt already used")
            cursor = db.execute(
                "INSERT INTO taxi_topups (driver_id, amount, receipt_file_id) VALUES (?, ?, ?)",
                (driver_id, amount, receipt_file_id),
            )
            return int(cursor.lastrowid)


def review_taxi_topup(topup_id: int, reviewer_id: int, approved: bool) -> tuple[sqlite3.Row, str | None] | None:
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            topup = db.execute(
                "SELECT * FROM taxi_topups WHERE id=? AND status='pending'", (topup_id,)
            ).fetchone()
            if not topup:
                db.rollback()
                return None
            status = "approved" if approved else "rejected"
            db.execute(
                "UPDATE taxi_topups SET status=?, reviewer_id=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, reviewer_id, topup_id),
            )
            if approved:
                changed = db.execute(
                    """UPDATE taxi_drivers SET
                    subscription_starts_at=COALESCE(subscription_starts_at, CURRENT_TIMESTAMP),
                    subscription_expires_at=datetime(
                        CASE WHEN subscription_expires_at > CURRENT_TIMESTAMP
                        THEN subscription_expires_at ELSE CURRENT_TIMESTAMP END, '+30 days'),
                    updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND is_active=1""",
                    (topup["driver_id"],),
                ).rowcount
                if changed != 1:
                    raise LookupError("driver unavailable")
                db.execute(
                    """INSERT INTO taxi_transactions
                    (driver_id, amount, kind, admin_id, note)
                    VALUES (?, ?, 'subscription', ?, ?)""",
                    (topup["driver_id"], topup["amount"], reviewer_id, f"Monthly subscription #{topup_id}"),
                )
                db.execute(
                    """UPDATE auto_driver_profiles SET status='active', updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=? AND status='payment_pending'""",
                    (topup["driver_id"],),
                )
            expiry = db.execute(
                "SELECT subscription_expires_at FROM taxi_drivers WHERE user_id=?", (topup["driver_id"],)
            ).fetchone()[0]
            db.commit()
            return topup, expiry
        except Exception:
            db.rollback()
            raise


def credit_driver(driver_id: int, amount: int, admin_id: int, note: str | None = None) -> int:
    if amount <= 0:
        raise ValueError("amount must be positive")
    with closing(_connect()) as db:
        with db:
            changed = db.execute(
                """UPDATE taxi_drivers SET balance=balance+?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=? AND is_active=1""",
                (amount, driver_id),
            ).rowcount
            if not changed:
                raise LookupError("driver not found")
            db.execute(
                """INSERT INTO taxi_transactions
                (driver_id, amount, kind, admin_id, note) VALUES (?, ?, 'credit', ?, ?)""",
                (driver_id, amount, admin_id, note),
            )
            return int(db.execute("SELECT balance FROM taxi_drivers WHERE user_id=?", (driver_id,)).fetchone()[0])


def list_drivers() -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            """SELECT user_id, username, full_name, is_active, is_suspended, balance,
            subscription_expires_at
            FROM taxi_drivers ORDER BY is_active DESC, balance DESC, registered_at"""
        ))


def taxi_control_stats() -> dict[str, int | float]:
    with closing(_connect()) as db:
        row = db.execute("""SELECT COUNT(*),
            SUM(CASE WHEN is_active=1 AND is_suspended=0 AND subscription_expires_at > CURRENT_TIMESTAMP THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_active=1 AND is_suspended=0 AND (subscription_expires_at IS NULL OR subscription_expires_at <= CURRENT_TIMESTAMP) THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_suspended=1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN is_active=1 AND is_suspended=0 AND date(subscription_expires_at) BETWEEN date('now') AND date('now','+2 days') THEN 1 ELSE 0 END)
            FROM taxi_drivers""").fetchone()
        orders = db.execute("SELECT COUNT(*), SUM(CASE WHEN status='new' THEN 1 ELSE 0 END), SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) FROM taxi_orders").fetchone()
        ratings = db.execute("SELECT COALESCE(AVG(stars),0), COUNT(*) FROM taxi_ratings").fetchone()
        return {"total": int(row[0]), "active": int(row[1] or 0), "unpaid": int(row[2] or 0),
                "suspended": int(row[3] or 0), "expiring": int(row[4] or 0),
                "orders": int(orders[0]), "new_orders": int(orders[1] or 0), "accepted_orders": int(orders[2] or 0),
                "rating": round(float(ratings[0]), 2), "ratings": int(ratings[1])}


def taxi_route_stats() -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            """SELECT r.route_key, r.label,
            COALESCE(MAX(o.route), r.label) AS route,
            COUNT(o.id) AS orders, COUNT(o.id) AS total,
            COALESCE(SUM(CASE WHEN o.status='new' THEN 1 ELSE 0 END),0) AS waiting,
            COALESCE(SUM(CASE WHEN o.status='new' THEN 1 ELSE 0 END),0) AS new_orders,
            COALESCE(SUM(CASE WHEN o.status IN ('accepted','completed') THEN 1 ELSE 0 END),0) AS accepted,
            COALESCE(SUM(CASE WHEN o.status='accepted' THEN 1 ELSE 0 END),0) AS accepted_orders,
            COALESCE(SUM(CASE WHEN o.status='completed' THEN 1 ELSE 0 END),0) AS completed,
            ROUND(AVG(CASE WHEN o.accepted_at IS NOT NULL
                THEN (julianday(o.accepted_at)-julianday(o.created_at))*86400 END),0) AS avg_accept_seconds
            FROM taxi_routes r LEFT JOIN taxi_orders o ON o.route_key=r.route_key
            WHERE r.is_active=1
            GROUP BY r.route_key,r.label,r.sort_order ORDER BY r.sort_order""",
        ))


def drivers_by_control_status(status: str, limit: int = 30) -> list[sqlite3.Row]:
    conditions = {
        "active": "is_active=1 AND is_suspended=0 AND subscription_expires_at > CURRENT_TIMESTAMP",
        "unpaid": "is_active=1 AND is_suspended=0 AND (subscription_expires_at IS NULL OR subscription_expires_at <= CURRENT_TIMESTAMP)",
        "suspended": "is_suspended=1",
        "expiring": "is_active=1 AND is_suspended=0 AND date(subscription_expires_at) BETWEEN date('now') AND date('now','+2 days')",
    }
    if status not in conditions:
        raise ValueError("invalid driver status")
    with closing(_connect()) as db:
        return list(db.execute(f"""SELECT user_id, username, full_name, subscription_expires_at
            FROM taxi_drivers WHERE {conditions[status]} ORDER BY updated_at DESC LIMIT ?""", (limit,)))


def eligible_driver_ids(route_key: str | None = None) -> list[int]:
    with closing(_connect()) as db:
        return [int(row[0]) for row in db.execute("""SELECT d.user_id FROM taxi_drivers d
            WHERE d.is_active=1 AND d.is_suspended=0
            AND d.subscription_expires_at > CURRENT_TIMESTAMP
            AND (? IS NULL OR NOT EXISTS (SELECT 1 FROM taxi_driver_routes x WHERE x.driver_id=d.user_id)
                 OR EXISTS (SELECT 1 FROM taxi_driver_routes x WHERE x.driver_id=d.user_id AND x.route_key=?))
            ORDER BY d.user_id""", (route_key, route_key))]


def finance_summary() -> dict[str, int]:
    with closing(_connect()) as db:
        row = db.execute(
            """SELECT
            COALESCE(SUM(CASE WHEN kind IN ('credit','subscription') THEN amount ELSE 0 END), 0),
            COALESCE(-SUM(CASE WHEN kind='commission' THEN amount ELSE 0 END), 0),
            COUNT(CASE WHEN kind='commission' THEN 1 END)
            FROM taxi_transactions"""
        ).fetchone()
        balance = db.execute("SELECT COALESCE(SUM(balance), 0) FROM taxi_drivers").fetchone()[0]
        return {"credits": int(row[0]), "revenue": int(row[1]), "orders": int(row[2]), "balances": int(balance)}


def control_finance_summary() -> dict[str, int]:
    with closing(_connect()) as db:
        taxi = db.execute("""SELECT
            COALESCE(SUM(CASE WHEN status='approved' THEN amount ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN status='approved' AND date(reviewed_at)=date('now') THEN amount ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN status='approved' AND strftime('%Y-%m',reviewed_at)=strftime('%Y-%m','now') THEN amount ELSE 0 END),0),
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) FROM taxi_topups""").fetchone()
        ads = db.execute("""SELECT
            COALESCE(SUM(CASE WHEN status='approved' THEN amount ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN status='approved' AND date(reviewed_at)=date('now') THEN amount ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN status='approved' AND strftime('%Y-%m',reviewed_at)=strftime('%Y-%m','now') THEN amount ELSE 0 END),0),
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) FROM ad_payments""").fetchone()
        return {"taxi_total": int(taxi[0]), "taxi_today": int(taxi[1]), "taxi_month": int(taxi[2]), "taxi_pending": int(taxi[3] or 0),
                "ads_total": int(ads[0]), "ads_today": int(ads[1]), "ads_month": int(ads[2]), "ads_pending": int(ads[3] or 0)}


def due_subscription_reminders(expiry_date: str) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute("""SELECT 'driver' subject_type, user_id subject_id,
            user_id recipient_id, subscription_expires_at expires_at, 'Такси ҳайдовчиси' title
            FROM taxi_drivers WHERE is_active=1 AND subscription_expires_at IS NOT NULL
            AND date(subscription_expires_at)=date(?)
            UNION ALL
            SELECT 'ad', id, owner_id, expires_at, title FROM ad_listings
            WHERE status='active' AND expires_at IS NOT NULL
            AND date(expires_at)=date(?)""", (expiry_date, expiry_date)))


def reserve_subscription_reminder(subject_type: str, subject_id: int, reminder_date: str, period: str) -> bool:
    with closing(_connect()) as db:
        with db:
            return db.execute("""INSERT OR IGNORE INTO subscription_reminders
                (subject_type, subject_id, reminder_date, period) VALUES (?, ?, ?, ?)""",
                (subject_type, subject_id, reminder_date, period)).rowcount == 1


def release_subscription_reminder(subject_type: str, subject_id: int, reminder_date: str, period: str) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute("""DELETE FROM subscription_reminders
                WHERE subject_type=? AND subject_id=? AND reminder_date=? AND period=?""",
                (subject_type, subject_id, reminder_date, period))


def set_taxi_driver_chat(chat_id: int, title: str | None) -> None:
    value = f"{chat_id}|{title or ''}"
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO app_settings (key, value) VALUES ('taxi_driver_chat', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
                (value,),
            )


def clear_taxi_driver_chat() -> None:
    with closing(_connect()) as db:
        with db:
            db.execute("DELETE FROM app_settings WHERE key='taxi_driver_chat'")


def taxi_driver_chat() -> tuple[int, str | None] | None:
    with closing(_connect()) as db:
        row = db.execute("SELECT value FROM app_settings WHERE key='taxi_driver_chat'").fetchone()
    if not row:
        return None
    raw_id, _, title = str(row["value"]).partition("|")
    try:
        return int(raw_id), title or None
    except ValueError:
        return None


def claim_order_with_commission(
    order_id: int,
    driver_id: int,
    commission: int,
    bypass_payment: bool = False,
) -> tuple[str, sqlite3.Row | None, str | None]:
    if commission < 0:
        raise ValueError("commission cannot be negative")
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            order = db.execute("SELECT * FROM taxi_orders WHERE id=?", (order_id,)).fetchone()
            if not order or order["status"] != "new":
                db.rollback()
                return "unavailable", None, None
            expiry: str | None = None
            if not bypass_payment:
                driver = db.execute(
                    "SELECT subscription_expires_at, is_suspended FROM taxi_drivers WHERE user_id=? AND is_active=1", (driver_id,)
                ).fetchone()
                if not driver:
                    db.rollback()
                    return "unregistered", None, None
                if driver["is_suspended"]:
                    db.rollback()
                    return "suspended", None, None
                expiry = driver["subscription_expires_at"]
                if not expiry or expiry <= db.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]:
                    db.rollback()
                    return "subscription_expired", None, expiry
                stats = db.execute("SELECT COALESCE(AVG(stars),0), COUNT(*) FROM taxi_ratings WHERE driver_id=?", (driver_id,)).fetchone()
                average, count = float(stats[0]), int(stats[1])
                wait_seconds = 0 if count >= 5 and average >= 4.5 else (30 if count >= 3 and average >= 3.5 else 60)
                age = float(db.execute("SELECT (julianday('now')-julianday(?))*86400", (order["created_at"],)).fetchone()[0])
                if age < wait_seconds:
                    db.rollback()
                    return "priority_wait", None, str(max(1, int(wait_seconds - age)))
            db.execute(
                "UPDATE taxi_orders SET status='accepted', driver_id=?, accepted_at=CURRENT_TIMESTAMP WHERE id=?",
                (driver_id, order_id),
            )
            accepted = db.execute("SELECT * FROM taxi_orders WHERE id=?", (order_id,)).fetchone()
            db.commit()
            return "accepted", accepted, expiry
        except Exception:
            db.rollback()
            raise


def recent_orders(limit: int = 10) -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute("SELECT * FROM taxi_orders ORDER BY id DESC LIMIT ?", (limit,)))


def claim_order(order_id: int, driver_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        with db:
            changed = db.execute(
                "UPDATE taxi_orders SET status='accepted', driver_id=?, accepted_at=CURRENT_TIMESTAMP WHERE id=? AND status='new'",
                (driver_id, order_id),
            ).rowcount
            if not changed:
                return None
            row = db.execute("SELECT * FROM taxi_orders WHERE id=?", (order_id,)).fetchone()
            return row


def set_prayer_reminder(user_id: int, prayer_key: str, enabled: bool) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO prayer_reminders (user_id, prayer_key, enabled)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, prayer_key) DO UPDATE SET
                    enabled=excluded.enabled, updated_at=CURRENT_TIMESTAMP""",
                (user_id, prayer_key, int(enabled)),
            )


def get_prayer_reminders(user_id: int) -> dict[str, bool]:
    with closing(_connect()) as db:
        rows = db.execute(
            "SELECT prayer_key, enabled FROM prayer_reminders WHERE user_id=?",
            (user_id,),
        )
        return {row["prayer_key"]: bool(row["enabled"]) for row in rows}


def enabled_prayer_users(prayer_key: str) -> list[int]:
    with closing(_connect()) as db:
        rows = db.execute(
            "SELECT user_id FROM prayer_reminders WHERE prayer_key=? AND enabled=1",
            (prayer_key,),
        )
        return [int(row["user_id"]) for row in rows]


def reserve_prayer_notification(user_id: int, prayer_key: str, prayer_date: str) -> bool:
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT OR IGNORE INTO prayer_notifications
                (user_id, prayer_key, prayer_date) VALUES (?, ?, ?)""",
                (user_id, prayer_key, prayer_date),
            )
            return cursor.rowcount == 1


def release_prayer_notification(user_id: int, prayer_key: str, prayer_date: str) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """DELETE FROM prayer_notifications
                WHERE user_id=? AND prayer_key=? AND prayer_date=?""",
                (user_id, prayer_key, prayer_date),
            )



def upsert_bot_user(user_id: int, username: str | None, first_name: str | None) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO bot_users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    is_active=1,
                    last_seen_at=CURRENT_TIMESTAMP""",
                (user_id, username, first_name),
            )


def active_bot_users() -> list[int]:
    with closing(_connect()) as db:
        rows = db.execute("SELECT user_id FROM bot_users WHERE is_active=1 ORDER BY user_id")
        return [int(row["user_id"]) for row in rows]


def set_bot_user_active(user_id: int, active: bool) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                "UPDATE bot_users SET is_active=?, last_seen_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (int(active), user_id),
            )


def reserve_daily_dua(user_id: int, delivery_date: str, dua_id: str) -> bool:
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT OR IGNORE INTO daily_dua_deliveries
                (user_id, delivery_date, dua_id) VALUES (?, ?, ?)""",
                (user_id, delivery_date, dua_id),
            )
            return cursor.rowcount == 1


def mark_daily_dua_status(user_id: int, delivery_date: str, status: str) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """UPDATE daily_dua_deliveries
                SET status=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=? AND delivery_date=?""",
                (status, user_id, delivery_date),
            )


def release_daily_dua(user_id: int, delivery_date: str) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                "DELETE FROM daily_dua_deliveries WHERE user_id=? AND delivery_date=? AND status='reserved'",
                (user_id, delivery_date),
            )


def add_daily_dua_group(chat_id: int, title: str | None, added_by: int) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO daily_dua_groups (chat_id, title, added_by)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title=excluded.title, added_by=excluded.added_by,
                    is_active=1, updated_at=CURRENT_TIMESTAMP""",
                (chat_id, title, added_by),
            )


def remove_daily_dua_group(chat_id: int) -> bool:
    with closing(_connect()) as db:
        with db:
            return db.execute(
                "UPDATE daily_dua_groups SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE chat_id=? AND is_active=1",
                (chat_id,),
            ).rowcount == 1


def active_daily_dua_groups() -> list[sqlite3.Row]:
    with closing(_connect()) as db:
        return list(db.execute(
            "SELECT chat_id, title FROM daily_dua_groups WHERE is_active=1 ORDER BY chat_id"
        ))


def reserve_daily_dua_group(chat_id: int, delivery_date: str, dua_id: str) -> bool:
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT OR IGNORE INTO daily_dua_group_deliveries
                (chat_id, delivery_date, dua_id) VALUES (?, ?, ?)""",
                (chat_id, delivery_date, dua_id),
            )
            return cursor.rowcount == 1


def mark_daily_dua_group_status(chat_id: int, delivery_date: str, status: str) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """UPDATE daily_dua_group_deliveries
                SET status=?, updated_at=CURRENT_TIMESTAMP
                WHERE chat_id=? AND delivery_date=?""",
                (status, chat_id, delivery_date),
            )


def release_daily_dua_group(chat_id: int, delivery_date: str) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """DELETE FROM daily_dua_group_deliveries
                WHERE chat_id=? AND delivery_date=? AND status='reserved'""",
                (chat_id, delivery_date),
            )


def record_daily_dua_stats(
    delivery_date: str,
    user_sent: int,
    group_sent: int,
    user_errors: int,
    group_errors: int,
) -> None:
    with closing(_connect()) as db:
        with db:
            db.execute(
                """INSERT INTO daily_dua_stats
                (delivery_date, user_sent, group_sent, user_errors, group_errors)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(delivery_date) DO UPDATE SET
                    user_sent=user_sent + excluded.user_sent,
                    group_sent=group_sent + excluded.group_sent,
                    user_errors=user_errors + excluded.user_errors,
                    group_errors=group_errors + excluded.group_errors,
                    updated_at=CURRENT_TIMESTAMP""",
                (delivery_date, user_sent, group_sent, user_errors, group_errors),
            )


def daily_dua_stats(delivery_date: str | None = None) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        if delivery_date:
            return db.execute(
                "SELECT * FROM daily_dua_stats WHERE delivery_date=?", (delivery_date,)
            ).fetchone()
        return db.execute(
            "SELECT * FROM daily_dua_stats ORDER BY delivery_date DESC LIMIT 1"
        ).fetchone()



ADMIN_TASK_STATUSES = {
    "new", "planned", "in_progress", "testing", "ready_for_approval",
    "approved", "deployed", "verified", "done", "blocked", "rejected",
    "failed", "rolled_back", "cancelled",
}


def create_admin_task(title: str, details: str, created_by: int) -> int:
    title = title.strip()
    details = details.strip()
    if not title or not details:
        raise ValueError("task title and details are required")
    if len(title) > 160 or len(details) > 4000:
        raise ValueError("task text is too long")
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                "INSERT INTO admin_tasks (title, details, created_by) VALUES (?, ?, ?)",
                (title, details, created_by),
            )
            task_id = int(cursor.lastrowid)
            agent_payload = json.dumps(
                {"title": title, "details": details, "created_by": created_by},
                ensure_ascii=False,
            )
            agent_cursor = db.execute(
                """INSERT INTO tasks
                (task_type, payload, source_admin_task_id, target_worker)
                VALUES ('manual_review', ?, ?, 'windows')""",
                (agent_payload, task_id),
            )
            db.execute(
                "UPDATE admin_tasks SET agent_task_id=? WHERE id=?",
                (int(agent_cursor.lastrowid), task_id),
            )
            db.execute(
                """INSERT INTO admin_task_events
                (task_id, actor_id, old_status, new_status, note)
                VALUES (?, ?, NULL, 'new', 'Телефон орқали вазифа яратилди')""",
                (task_id, created_by),
            )
            return task_id


SAFE_CONTROL_TASK_TARGETS = {
    "repository_status": "nexus",
    "run_tests": "nexus",
    "health_check": "nexus",
    "security_audit": "nexus",
    "bridge_audit": "nexus",
    "windows_health": "windows",
    "archivist_inventory": "windows",
    "windows_agent_update": "windows",
}



CLOSEOUT_BATCH = (
    "windows_agent_update",
    "windows_health",
    "archivist_inventory",
    "bridge_audit",
    "security_audit",
    "health_check",
    "repository_status",
    "repository_status",
    "repository_status",
    "repository_status",
    "repository_status",
)


def create_closeout_batch(created_by: int) -> list[int]:
    """Queue one fixed safe closeout batch.

    The final five repository_status tasks are deliberate consecutive E2E probes.
    They exercise Control Center -> queue -> NEXUS worker -> report -> result
    without arbitrary shell or mutable payload.
    """
    return [create_control_task(task_type, created_by) for task_type in CLOSEOUT_BATCH]


def guardian_archivist_snapshot() -> dict[str, sqlite3.Row | None]:
    """Return latest result row for the Guardian/Archivist control tasks."""
    wanted = (
        "security_audit",
        "bridge_audit",
        "health_check",
        "windows_health",
        "archivist_inventory",
        "windows_agent_update",
    )
    result: dict[str, sqlite3.Row | None] = {name: None for name in wanted}
    with closing(_connect()) as db:
        rows = db.execute(
            """SELECT a.id, a.title, a.status, a.updated_at,
                      t.task_type, t.target_worker, t.report
               FROM admin_tasks a
               JOIN tasks t ON t.id=a.agent_task_id
               WHERE t.task_type IN (?,?,?,?,?,?)
               ORDER BY a.id DESC""",
            wanted,
        ).fetchall()
    for row in rows:
        key = str(row["task_type"])
        if result[key] is None:
            result[key] = row
    return result


def create_control_task(task_type: str, created_by: int) -> int:
    target_worker = SAFE_CONTROL_TASK_TARGETS.get(task_type)
    if not target_worker:
        raise ValueError("unsupported safe control task type")
    titles = {
        "repository_status": "Git repository status",
        "run_tests": "Run automated tests",
        "health_check": "NEXUS worker health check",
        "security_audit": "NEXUS Guardian security audit",
        "bridge_audit": "Existing NEXUS bridge audit",
        "windows_health": "Windows health audit",
        "archivist_inventory": "ARCHIVIST read-only inventory",
        "windows_agent_update": "Windows agent safe update",
    }
    title = titles[task_type]
    details = f"Safe fixed control task: {task_type}"
    with closing(_connect()) as db:
        with db:
            cursor = db.execute(
                """INSERT INTO admin_tasks
                (title, details, status, created_by)
                VALUES (?, ?, 'planned', ?)""",
                (title, details, created_by),
            )
            admin_task_id = int(cursor.lastrowid)
            agent_cursor = db.execute(
                """INSERT INTO tasks
                (task_type, payload, source_admin_task_id, target_worker)
                VALUES (?, '{}', ?, ?)""",
                (task_type, admin_task_id, target_worker),
            )
            agent_task_id = int(agent_cursor.lastrowid)
            db.execute(
                "UPDATE admin_tasks SET agent_task_id=? WHERE id=?",
                (agent_task_id, admin_task_id),
            )
            db.execute(
                """INSERT INTO admin_task_events
                (task_id, actor_id, old_status, new_status, note)
                VALUES (?, ?, NULL, 'planned', 'Хавфсиз NEXUS вазифаси яратилди')""",
                (admin_task_id, created_by),
            )
            return admin_task_id


def list_admin_tasks(limit: int = 10, include_closed: bool = False) -> list[sqlite3.Row]:
    safe_limit = max(1, min(int(limit), 50))
    with closing(_connect()) as db:
        if include_closed:
            return list(db.execute(
                "SELECT * FROM admin_tasks ORDER BY id DESC LIMIT ?", (safe_limit,)
            ))
        return list(db.execute(
            """SELECT * FROM admin_tasks
            WHERE status NOT IN ('done','cancelled','rejected')
            ORDER BY id DESC LIMIT ?""",
            (safe_limit,),
        ))


def recent_task_results(limit: int = 10) -> list[sqlite3.Row]:
    safe_limit = max(1, min(int(limit), 20))
    with closing(_connect()) as db:
        return list(
            db.execute(
                """SELECT a.id, a.title, a.status, a.updated_at,
                          t.task_type, t.target_worker, t.report
                FROM admin_tasks a
                LEFT JOIN tasks t ON t.id=a.agent_task_id
                WHERE a.status IN ('done','failed','ready_for_approval','blocked','rolled_back')
                   OR t.report IS NOT NULL
                ORDER BY a.id DESC
                LIMIT ?""",
                (safe_limit,),
            )
        )


def admin_task(task_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as db:
        return db.execute("SELECT * FROM admin_tasks WHERE id=?", (task_id,)).fetchone()


def set_admin_task_status(task_id: int, status: str, actor_id: int, note: str = "") -> bool:
    if status not in ADMIN_TASK_STATUSES:
        raise ValueError("unknown task status")
    with closing(_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute("SELECT status FROM admin_tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                db.rollback()
                return False
            old_status = str(row["status"])
            if old_status == status:
                db.rollback()
                return True
            db.execute(
                "UPDATE admin_tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, task_id),
            )
            if status == "cancelled":
                db.execute(
                    """UPDATE tasks SET status='cancelled', updated_at=CURRENT_TIMESTAMP
                    WHERE source_admin_task_id=? AND status='pending'""",
                    (task_id,),
                )
            db.execute(
                """INSERT INTO admin_task_events
                (task_id, actor_id, old_status, new_status, note)
                VALUES (?, ?, ?, ?, ?)""",
                (task_id, actor_id, old_status, status, note.strip()[:1000] or None),
            )
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
