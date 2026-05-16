import sqlite3
from contextlib import contextmanager
from typing import Optional
from datetime import datetime
import threading
import time


DB_PATH = "steam_flip.db"


_thread_local_db = threading.local()


def get_db_connection():
    conn = getattr(_thread_local_db, 'connection', None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _thread_local_db.connection = conn
    return conn


@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            item_name TEXT NOT NULL,
            note TEXT,
            unit_cost REAL NOT NULL,
            unit_steam_sell REAL NOT NULL,
            qty INTEGER NOT NULL,
            unit_net REAL NOT NULL,
            total_cost REAL NOT NULL,
            total_steam_sell REAL NOT NULL,
            total_net REAL NOT NULL,
            sell_currency TEXT NOT NULL DEFAULT 'CNY',
            sell_currency_symbol TEXT NOT NULL DEFAULT '¥',
            exchange_rate REAL NOT NULL DEFAULT 1.0,
            my_currency TEXT NOT NULL DEFAULT 'CNY',
            my_currency_symbol TEXT NOT NULL DEFAULT '¥',
            total_cost_in_my_currency REAL NOT NULL DEFAULT 0,
            total_net_in_my_currency REAL NOT NULL DEFAULT 0,
            total_steam_sell_in_my_currency REAL NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            buy_currency TEXT NOT NULL DEFAULT 'CNY',
            buy_currency_symbol TEXT NOT NULL DEFAULT '¥',
            sell_currency TEXT NOT NULL DEFAULT 'CNY',
            sell_currency_symbol TEXT NOT NULL DEFAULT '¥',
            exchange_rate REAL NOT NULL DEFAULT 1.0,
            steam_fee_rate REAL NOT NULL DEFAULT 0.15,
            theme_mode TEXT NOT NULL DEFAULT 'LIGHT',
            my_currency TEXT NOT NULL DEFAULT 'CNY',
            my_currency_symbol TEXT NOT NULL DEFAULT '¥',
            exchange_rate_updated_at TEXT,
            language TEXT NOT NULL DEFAULT 'zh'
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_id_desc ON history(id DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_ts_desc ON history(ts DESC)")
    
    # 升级历史表，添加货币相关字段
    cur.execute("PRAGMA table_info(history)")
    history_columns = [col[1] for col in cur.fetchall()]
    if "sell_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN sell_currency TEXT NOT NULL DEFAULT 'CNY'")
    if "sell_currency_symbol" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN sell_currency_symbol TEXT NOT NULL DEFAULT '¥'")
    if "exchange_rate" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN exchange_rate REAL NOT NULL DEFAULT 1.0")
    if "my_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN my_currency TEXT NOT NULL DEFAULT 'CNY'")
    if "my_currency_symbol" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN my_currency_symbol TEXT NOT NULL DEFAULT '¥'")
    if "total_cost_in_my_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN total_cost_in_my_currency REAL NOT NULL DEFAULT 0")
    if "total_net_in_my_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN total_net_in_my_currency REAL NOT NULL DEFAULT 0")
    if "total_steam_sell_in_my_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN total_steam_sell_in_my_currency REAL NOT NULL DEFAULT 0")
    
    cur.execute("PRAGMA table_info(settings)")
    columns = [col[1] for col in cur.fetchall()]
    if "theme_mode" not in columns:
        cur.execute("ALTER TABLE settings ADD COLUMN theme_mode TEXT NOT NULL DEFAULT 'LIGHT'")
    if "my_currency" not in columns:
        cur.execute("ALTER TABLE settings ADD COLUMN my_currency TEXT NOT NULL DEFAULT 'CNY'")
    if "my_currency_symbol" not in columns:
        cur.execute("ALTER TABLE settings ADD COLUMN my_currency_symbol TEXT NOT NULL DEFAULT '¥'")
    if "exchange_rate_updated_at" not in columns:
        cur.execute("ALTER TABLE settings ADD COLUMN exchange_rate_updated_at TEXT")
    if "language" not in columns:
        cur.execute("ALTER TABLE settings ADD COLUMN language TEXT NOT NULL DEFAULT 'zh'")
    cur.execute("SELECT COUNT(*) FROM settings")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO settings (id) VALUES (1)")
    conn.commit()
    conn.close()


class CacheManager:
    def __init__(self, ttl: int = 5):
        self._cache = {
            "data": None,
            "timestamp": 0,
            "ttl": ttl
        }

    def is_valid(self) -> bool:
        if self._cache["data"] is None:
            return False
        elapsed = time.time() - self._cache["timestamp"]
        return elapsed < self._cache["ttl"]

    def get(self):
        return self._cache["data"]

    def set(self, data):
        self._cache["data"] = data
        self._cache["timestamp"] = time.time()

    def invalidate(self):
        self._cache["data"] = None
        self._cache["timestamp"] = 0


_settings_cache = CacheManager(ttl=5)
_stats_cache = CacheManager(ttl=5)


def invalidate_settings_cache():
    _settings_cache.invalidate()


def invalidate_stats_cache():
    _stats_cache.invalidate()


def get_exchange_rate_cached(base: str, target: str, force_refresh: bool = False):
    if base == target:
        return 1.0, None, "相同货币"
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT exchange_rate, exchange_rate_updated_at FROM settings WHERE id = 1")
        row = cur.fetchone()
        
        cached_rate = None
        cached_time = None
        if row:
            cached_rate = row["exchange_rate"]
            cached_time = row["exchange_rate_updated_at"]
        
        if not force_refresh and cached_rate is not None and cached_time is not None:
            try:
                cached_datetime = datetime.strptime(cached_time, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                diff_hours = (now - cached_datetime).total_seconds() / 3600
                if diff_hours < 12:
                    return cached_rate, cached_time, "使用缓存"
            except Exception:
                pass
    
    try:
        import requests
        url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if target not in data.get("rates", {}):
            return cached_rate or 1.0, cached_time, "获取失败，使用缓存"
        
        rate = round(data["rates"][target], 4)
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE settings SET exchange_rate = ?, exchange_rate_updated_at = ? WHERE id = 1",
                (rate, updated_at)
            )
        
        invalidate_settings_cache()
        
        return rate, updated_at, "获取成功"
    except Exception as e:
        return cached_rate or 1.0, cached_time, f"获取失败: {str(e)}"