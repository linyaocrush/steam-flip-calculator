import sqlite3
from contextlib import contextmanager
from datetime import datetime
import threading
import time
import os
from typing import Optional, Dict, Any, List
from config import DB_PATH, DATA_DIR
from models import Settings, HistoryRecord, StatsData, Currency

_thread_local_db = threading.local()


def get_db_connection():
    conn = getattr(_thread_local_db, 'connection', None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
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
    os.makedirs(DATA_DIR, exist_ok=True)
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
            buy_currency TEXT NOT NULL DEFAULT 'CNY',
            buy_currency_symbol TEXT NOT NULL DEFAULT '¥',
            exchange_rate REAL NOT NULL DEFAULT 1.0,
            my_currency TEXT NOT NULL DEFAULT 'CNY',
            my_currency_symbol TEXT NOT NULL DEFAULT '¥',
            total_cost_in_my_currency REAL NOT NULL DEFAULT 0,
            total_net_in_my_currency REAL NOT NULL DEFAULT 0,
            total_steam_sell_in_my_currency REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0
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
    
    cur.execute("SELECT COUNT(*) FROM settings")
    if cur.fetchone()[0] == 0:
        default_settings = Settings()
        cur.execute(
            """
            INSERT INTO settings (id, buy_currency, buy_currency_symbol, sell_currency, sell_currency_symbol,
                                exchange_rate, steam_fee_rate, theme_mode, my_currency, my_currency_symbol, language)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                default_settings.buy_currency,
                default_settings.buy_currency_symbol,
                default_settings.sell_currency,
                default_settings.sell_currency_symbol,
                default_settings.exchange_rate,
                default_settings.steam_fee_rate,
                default_settings.theme_mode,
                default_settings.my_currency,
                default_settings.my_currency_symbol,
                default_settings.language,
            )
        )
    
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


def get_settings() -> Settings:
    if _settings_cache.is_valid():
        return _settings_cache.get()

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM settings WHERE id = 1")
        row = cur.fetchone()
        
        if row:
            settings_data = {
                "buy_currency": row["buy_currency"],
                "buy_currency_symbol": row["buy_currency_symbol"],
                "sell_currency": row["sell_currency"],
                "sell_currency_symbol": row["sell_currency_symbol"],
                "exchange_rate": row["exchange_rate"],
                "steam_fee_rate": row["steam_fee_rate"],
                "theme_mode": row["theme_mode"],
                "my_currency": row["my_currency"],
                "my_currency_symbol": row["my_currency_symbol"],
                "exchange_rate_updated_at": row["exchange_rate_updated_at"],
                "language": row["language"]
            }
            settings = Settings(**settings_data)
        else:
            settings = Settings()

    _settings_cache.set(settings)
    return settings


def save_settings(settings: Settings) -> Settings:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE settings SET 
                buy_currency = ?, 
                buy_currency_symbol = ?, 
                sell_currency = ?, 
                sell_currency_symbol = ?, 
                exchange_rate = ?, 
                steam_fee_rate = ?,
                theme_mode = ?,
                my_currency = ?,
                my_currency_symbol = ?,
                language = ?
            WHERE id = 1
            """,
            (
                settings.buy_currency,
                settings.buy_currency_symbol,
                settings.sell_currency,
                settings.sell_currency_symbol,
                settings.exchange_rate,
                settings.steam_fee_rate,
                settings.theme_mode,
                settings.my_currency,
                settings.my_currency_symbol,
                settings.language
            )
        )

    invalidate_settings_cache()
    invalidate_stats_cache()

    return settings


def get_records(limit: int = 500) -> List[HistoryRecord]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ts, item_name, COALESCE(note, '') as note,
                   unit_cost, unit_steam_sell, qty, unit_net, total_cost, total_net,
                   sell_currency, sell_currency_symbol, buy_currency, buy_currency_symbol,
                   exchange_rate, my_currency, my_currency_symbol,
                   total_cost_in_my_currency, total_net_in_my_currency, discount
            FROM history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cur.fetchall()

    records = []
    for row in rows:
        record_data = {
            "id": row["id"],
            "ts": row["ts"],
            "item_name": row["item_name"],
            "note": row["note"] if row["note"] else None,
            "unit_cost": row["unit_cost"],
            "unit_steam_sell": row["unit_steam_sell"],
            "qty": row["qty"],
            "unit_net": row["unit_net"],
            "total_cost": row["total_cost"],
            "total_steam_sell": row["total_cost"] + row["total_net"],
            "total_net": row["total_net"],
            "sell_currency": row["sell_currency"],
            "sell_currency_symbol": row["sell_currency_symbol"],
            "buy_currency": row["buy_currency"],
            "buy_currency_symbol": row["buy_currency_symbol"],
            "exchange_rate": row["exchange_rate"],
            "my_currency": row["my_currency"],
            "my_currency_symbol": row["my_currency_symbol"],
            "total_cost_in_my_currency": row["total_cost_in_my_currency"],
            "total_net_in_my_currency": row["total_net_in_my_currency"],
            "total_steam_sell_in_my_currency": row["total_cost_in_my_currency"] + row["total_net_in_my_currency"],
            "discount": row["discount"]
        }
        records.append(HistoryRecord(**record_data))

    return records


def add_record(record: HistoryRecord) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT sell_currency, sell_currency_symbol, buy_currency, buy_currency_symbol, my_currency, my_currency_symbol, exchange_rate FROM settings WHERE id = 1")
        row = cur.fetchone()
        sell_currency = row["sell_currency"] if row else "CNY"
        sell_currency_symbol = row["sell_currency_symbol"] if row else "¥"
        buy_currency = row["buy_currency"] if row else "CNY"
        buy_currency_symbol = row["buy_currency_symbol"] if row else "¥"
        my_currency = row["my_currency"] if row else "CNY"
        my_currency_symbol = row["my_currency_symbol"] if row else "¥"
        exchange_rate = row["exchange_rate"] if row else 1.0
        
        ts = record.ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            """
            INSERT INTO history (ts, item_name, note, unit_cost, unit_steam_sell,
                                qty, unit_net, total_cost, total_steam_sell, total_net,
                                sell_currency, sell_currency_symbol,
                                buy_currency, buy_currency_symbol,
                                exchange_rate,
                                my_currency, my_currency_symbol,
                                total_cost_in_my_currency, total_net_in_my_currency,
                                total_steam_sell_in_my_currency, discount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, record.item_name, record.note, record.unit_cost, record.unit_steam_sell, record.qty,
             record.unit_net, record.total_cost, record.total_steam_sell, record.total_net,
             sell_currency, sell_currency_symbol,
             buy_currency, buy_currency_symbol,
             exchange_rate,
             my_currency, my_currency_symbol,
             record.total_cost_in_my_currency, record.total_net_in_my_currency,
             record.total_steam_sell_in_my_currency, record.discount),
        )

    invalidate_stats_cache()
    return True


def delete_record(record_id: int) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM history WHERE id = ?", (record_id,))

    invalidate_stats_cache()
    return True


def clear_records() -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM history")

    invalidate_stats_cache()
    return True


def get_stats() -> StatsData:
    if _stats_cache.is_valid():
        return _stats_cache.get()

    with get_db() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT my_currency, my_currency_symbol FROM settings WHERE id = 1")
        row = cur.fetchone()
        my_currency = row["my_currency"] if row else "CNY"
        my_currency_symbol = row["my_currency_symbol"] if row else "¥"
        
        cur.execute(
            """
            SELECT 
                COUNT(*) as count,
                SUM(total_cost_in_my_currency) as total_cost,
                SUM(total_net_in_my_currency) as total_net,
                SUM(total_steam_sell_in_my_currency) as total_sell,
                SUM(qty) as total_qty
            FROM history
            """
        )
        row = cur.fetchone()
        
        if row and row["count"] > 0:
            stats_data = {
                "total_cost": row["total_cost"] or 0.0,
                "total_net": row["total_net"] or 0.0,
                "total_sell": row["total_sell"] or 0.0,
                "total_qty": row["total_qty"] or 0,
                "avg_ratio": (row["total_net"] / row["total_cost"]) if row["total_cost"] > 0 else 0.0,
                "avg_discount": 0.0
            }
            
            cur.execute(
                """
                SELECT AVG(discount) as avg_discount
                FROM history
                WHERE discount IS NOT NULL
                """
            )
            discount_row = cur.fetchone()
            if discount_row and discount_row["avg_discount"]:
                stats_data["avg_discount"] = discount_row["avg_discount"]
        else:
            stats_data = {
                "total_cost": 0.0,
                "total_net": 0.0,
                "total_sell": 0.0,
                "total_qty": 0,
                "avg_ratio": 0.0,
                "avg_discount": 0.0
            }

    stats = StatsData(**stats_data)
    _stats_cache.set(stats)
    return stats


def update_exchange_rate_updated_at(timestamp: Optional[str] = None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE settings SET exchange_rate_updated_at = ? WHERE id = 1",
            (timestamp,)
        )
    
    invalidate_settings_cache()