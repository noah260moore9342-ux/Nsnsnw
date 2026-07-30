import aiosqlite
import datetime
import uuid
from config import DATABASE_URL

DB = DATABASE_URL


def _id():
    return str(uuid.uuid4())


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id           TEXT PRIMARY KEY,
                number       TEXT NOT NULL,
                password     TEXT DEFAULT '',
                twofa        TEXT DEFAULT '',
                session_str  TEXT DEFAULT '',
                country      TEXT DEFAULT 'India',
                country_flag TEXT DEFAULT '🇮🇳',
                price        REAL NOT NULL,
                description  TEXT DEFAULT '',
                status       TEXT DEFAULT 'available',
                added_at     TEXT NOT NULL,
                sold_at      TEXT DEFAULT NULL,
                sold_to      INTEGER DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id           TEXT PRIMARY KEY,
                user_id      INTEGER NOT NULL,
                username     TEXT DEFAULT '',
                full_name    TEXT DEFAULT '',
                account_id   TEXT NOT NULL,
                amount       REAL NOT NULL,
                screenshot   TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                created_at   TEXT NOT NULL,
                approved_at  TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT DEFAULT '',
                full_name    TEXT DEFAULT '',
                joined_at    TEXT NOT NULL,
                total_spent  REAL DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                is_banned    INTEGER DEFAULT 0,
                ban_reason   TEXT DEFAULT '',
                balance      REAL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS otp_sessions (
                id           TEXT PRIMARY KEY,
                order_id     TEXT NOT NULL,
                user_id      INTEGER NOT NULL,
                account_id   TEXT NOT NULL,
                otp_code     TEXT DEFAULT '',
                status       TEXT DEFAULT 'waiting',
                created_at   TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id           TEXT PRIMARY KEY,
                user_id      INTEGER NOT NULL,
                username     TEXT DEFAULT '',
                amount       REAL NOT NULL,
                exact_amount REAL DEFAULT 0,
                screenshot   TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                created_at   TEXT NOT NULL,
                approved_at  TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            )
        """)
        await db.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance','0')")
        await db.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance_msg','🔧 Bot is under maintenance. Please check back later!')")
        await db.commit()


# ── Settings ──────────────────────────────────────────────────────────────────

async def get_setting(key):
    async with aiosqlite.connect(DB) as db:
        r = await (await db.execute("SELECT value FROM settings WHERE key=?", (key,))).fetchone()
        return r[0] if r else ""

async def set_setting(key, value):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))
        await db.commit()

async def is_maintenance():
    return (await get_setting("maintenance")) == "1"

async def get_maintenance_msg():
    return await get_setting("maintenance_msg")


# ── Accounts ──────────────────────────────────────────────────────────────────

async def add_account(number, price, country, country_flag,
                      password="", twofa="", session_str="", description=""):
    now = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_id(), number, password, twofa, session_str,
             country, country_flag, price, description, "available", now, None, None)
        )
        await db.commit()

async def get_available_accounts():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM accounts WHERE status='available' ORDER BY country") as c:
            return [dict(r) for r in await c.fetchall()]

async def get_available_by_country(country):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM accounts WHERE status='available' AND country=?", (country,)) as c:
            return [dict(r) for r in await c.fetchall()]

async def get_country_stock():
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT country, country_flag, price, COUNT(*) FROM accounts WHERE status='available' GROUP BY country ORDER BY country"
        ) as c:
            return [{"country": r[0], "flag": r[1], "price": r[2], "count": r[3]} for r in await c.fetchall()]

async def get_account(account_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)) as c:
            r = await c.fetchone()
            return dict(r) if r else None

async def get_all_accounts():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM accounts ORDER BY status, added_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]

async def mark_account_sold(account_id, user_id):
    now = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE accounts SET status='sold',sold_at=?,sold_to=? WHERE id=?", (now, user_id, account_id))
        await db.commit()

async def delete_account(account_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        await db.commit()

async def update_account(account_id, **kwargs):
    allowed = ["price","password","twofa","session_str","description","country","country_flag"]
    sets = ", ".join(f"{k}=?" for k in kwargs if k in allowed)
    vals = [v for k,v in kwargs.items() if k in allowed]
    if not sets:
        return
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE accounts SET {sets} WHERE id=?", (*vals, account_id))
        await db.commit()


# ── Orders ────────────────────────────────────────────────────────────────────

async def create_order(user_id, username, full_name, account_id, amount):
    now = datetime.datetime.now().isoformat()
    oid = _id()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)",
            (oid, user_id, username, full_name, account_id, amount, "", "pending", now, None)
        )
        await db.commit()
    return oid

async def get_order(order_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id=?", (order_id,)) as c:
            r = await c.fetchone()
            return dict(r) if r else None

async def get_pending_orders():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]

async def get_all_orders(limit=50):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)) as c:
            return [dict(r) for r in await c.fetchall()]

async def get_user_orders(user_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (user_id,)) as c:
            return [dict(r) for r in await c.fetchall()]

async def approve_order(order_id):
    now = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE orders SET status='approved',approved_at=? WHERE id=?", (now, order_id))
        await db.commit()

async def reject_order(order_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
        await db.commit()

async def set_order_screenshot(order_id, file_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE orders SET screenshot=? WHERE id=?", (file_id, order_id))
        await db.commit()


# ── Users ─────────────────────────────────────────────────────────────────────

async def upsert_user(user_id, username, full_name):
    now = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        r = await (await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))).fetchone()
        if not r:
            await db.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, username, full_name, now, 0, 0, 0, "", 0)
            )
        else:
            await db.execute("UPDATE users SET username=?,full_name=? WHERE user_id=?", (username, full_name, user_id))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as c:
            r = await c.fetchone()
            return dict(r) if r else None

async def get_all_users():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY joined_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]

async def update_user_stats(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET total_spent=total_spent+?,total_orders=total_orders+1 WHERE user_id=?", (amount, user_id))
        await db.commit()

async def ban_user(user_id, reason="No reason provided"):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET is_banned=1,ban_reason=? WHERE user_id=?", (reason, user_id))
        await db.commit()

async def unban_user(user_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET is_banned=0,ban_reason='' WHERE user_id=?", (user_id,))
        await db.commit()

async def is_banned(user_id):
    async with aiosqlite.connect(DB) as db:
        r = await (await db.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))).fetchone()
        return bool(r and r[0])

async def get_balance(user_id):
    async with aiosqlite.connect(DB) as db:
        r = await (await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))).fetchone()
        return float(r[0]) if r else 0.0

async def add_balance(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def deduct_balance(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        r = await (await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))).fetchone()
        if not r or float(r[0]) < amount:
            return False
        await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, user_id))
        await db.commit()
        return True


# ── Deposits ──────────────────────────────────────────────────────────────────

async def create_deposit(user_id, username, amount, exact_amount):
    now = datetime.datetime.now().isoformat()
    did = _id()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO deposits VALUES (?,?,?,?,?,?,?,?,?)",
            (did, user_id, username, amount, exact_amount, "", "pending", now, None)
        )
        await db.commit()
    return did

async def get_deposit(deposit_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deposits WHERE id=?", (deposit_id,)) as c:
            r = await c.fetchone()
            return dict(r) if r else None

async def set_deposit_screenshot(deposit_id, file_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE deposits SET screenshot=? WHERE id=?", (file_id, deposit_id))
        await db.commit()

async def approve_deposit(deposit_id):
    now = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        r = await (await db.execute("SELECT * FROM deposits WHERE id=?", (deposit_id,))).fetchone()
        if r:
            await db.execute("UPDATE deposits SET status='approved',approved_at=? WHERE id=?", (now, deposit_id))
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (r[3], r[1]))
            await db.commit()

async def reject_deposit(deposit_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE deposits SET status='rejected' WHERE id=?", (deposit_id,))
        await db.commit()

async def get_pending_deposits():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deposits WHERE status='pending' ORDER BY created_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]

async def update_deposit_exact(deposit_id, exact_amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE deposits SET exact_amount=? WHERE id=?", (exact_amount, deposit_id))
        await db.commit()


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_stats():
    async with aiosqlite.connect(DB) as db:
        ta  = (await (await db.execute("SELECT COUNT(*) FROM accounts")).fetchone())[0]
        av  = (await (await db.execute("SELECT COUNT(*) FROM accounts WHERE status='available'")).fetchone())[0]
        sol = (await (await db.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'")).fetchone())[0]
        tu  = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        ban = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")).fetchone())[0]
        po  = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")).fetchone())[0]
        ao  = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='approved'")).fetchone())[0]
        pd  = (await (await db.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'")).fetchone())[0]
        rev = (await (await db.execute("SELECT SUM(amount) FROM orders WHERE status='approved'")).fetchone())[0] or 0
        return {"total_accounts":ta,"available":av,"sold":sol,"users":tu,"banned":ban,
                "pending":po,"approved_orders":ao,"pending_deposits":pd,"revenue":rev}


# ── OTP Sessions ──────────────────────────────────────────────────────────────

async def create_otp_session(order_id, user_id, account_id):
    now = datetime.datetime.now().isoformat()
    sid = _id()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO otp_sessions VALUES (?,?,?,?,?,?,?)",
            (sid, order_id, user_id, account_id, "", "waiting", now)
        )
        await db.commit()
    return sid

async def get_otp_session(session_id):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM otp_sessions WHERE id=?", (session_id,)) as c:
            r = await c.fetchone()
            return dict(r) if r else None

async def deliver_otp(session_id, otp_code):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE otp_sessions SET otp_code=?,status='delivered' WHERE id=?", (otp_code, session_id))
        await db.commit()

async def get_waiting_otp_sessions():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM otp_sessions WHERE status='waiting' ORDER BY created_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]
