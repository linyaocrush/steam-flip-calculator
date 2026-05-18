import sqlite3
from contextlib import contextmanager
from datetime import datetime
import threading
import time
from typing import Optional, Dict, Any
from config import DB_PATH

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
        from config import DEFAULT_SETTINGS
        cur.execute(
            """
            INSERT INTO settings (id, buy_currency, buy_currency_symbol, sell_currency, sell_currency_symbol,
                                exchange_rate, steam_fee_rate, theme_mode, my_currency, my_currency_symbol, language)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_SETTINGS["buy_currency"],
                DEFAULT_SETTINGS["buy_currency_symbol"],
                DEFAULT_SETTINGS["sell_currency"],
                DEFAULT_SETTINGS["sell_currency_symbol"],
                DEFAULT_SETTINGS["exchange_rate"],
                DEFAULT_SETTINGS["steam_fee_rate"],
                DEFAULT_SETTINGS["theme_mode"],
                DEFAULT_SETTINGS["my_currency"],
                DEFAULT_SETTINGS["my_currency_symbol"],
                DEFAULT_SETTINGS["language"],
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


def get_settings() -> Dict[str, Any]:
    if _settings_cache.is_valid():
        return _settings_cache.get()

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM settings WHERE id = 1")
        row = cur.fetchone()
        
        if row:
            response_data = {
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
        else:
            from config import DEFAULT_SETTINGS
            response_data = DEFAULT_SETTINGS.copy()

    _settings_cache.set(response_data)
    return response_data


def save_settings(data: Dict[str, Any]) -> Dict[str, Any]:
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
                data["buy_currency"],
                data["buy_currency_symbol"],
                data["sell_currency"],
                data["sell_currency_symbol"],
                data["exchange_rate"],
                data["steam_fee_rate"],
                data["theme_mode"],
                data["my_currency"],
                data["my_currency_symbol"],
                data["language"]
            )
        )

    invalidate_settings_cache()
    invalidate_stats_cache()

    return data


def get_records(limit: int = 500) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ts, item_name, COALESCE(note, '') as note,
                   unit_cost, unit_steam_sell, qty, unit_net, total_cost, total_net,
                   sell_currency_symbol, buy_currency_symbol, my_currency_symbol,
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
        records.append({
            "id": row["id"],
            "ts": row["ts"],
            "item_name": row["item_name"],
            "note": row["note"],
            "unit_cost": row["unit_cost"],
            "unit_steam_sell": row["unit_steam_sell"],
            "qty": row["qty"],
            "unit_net": row["unit_net"],
            "total_cost": row["total_cost"],
            "total_net": row["total_net"],
            "total_cost_in_my_currency": row["total_cost_in_my_currency"],
            "total_net_in_my_currency": row["total_net_in_my_currency"],
            "sell_currency_symbol": row["sell_currency_symbol"],
            "buy_currency_symbol": row["buy_currency_symbol"],
            "my_currency_symbol": row["my_currency_symbol"],
            "discount": row["discount"]
        })

    return records


def add_record(data: Dict[str, Any]) -> bool:
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
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            (ts, data["item_name"], data["note"], data["unit_cost"], data["unit_steam_sell"], data["qty"],
             data["unit_net"], data["total_cost"], data["total_steam_sell"], data["total_net"],
             sell_currency, sell_currency_symbol,
             buy_currency, buy_currency_symbol,
             exchange_rate,
             my_currency, my_currency_symbol,
             data["total_cost_in_my_currency"], data["total_net_in_my_currency"],
             data["total_steam_sell_in_my_currency"], data["discount"]),
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


def get_stats() -> Dict[str, Any]:
    if _stats_cache.is_valid():
        return _stats_cache.get()

    with get_db() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT my_currency, my_currency_symbol FROM settings WHERE id = 1")
        settings_row = cur.fetchone()
        current_my_currency = settings_row["my_currency"] if settings_row else "CNY"
        current_my_currency_symbol = settings_row["my_currency_symbol"] if settings_row else "¥"
        
        cur.execute(
            """
            SELECT
                COALESCE(SUM(total_cost_in_my_currency), 0),
                COALESCE(SUM(total_net_in_my_currency), 0),
                COALESCE(SUM(total_steam_sell_in_my_currency), 0),
                COALESCE(SUM(qty), 0)
            FROM history
            """
        )
        total_cost, total_net, total_steam_sell, total_qty = cur.fetchone()

    ratio = (total_cost / total_net) if total_net > 0 else 0.0
    discount = (1.0 - ratio) if total_net > 0 else 0.0

    response_data = {
        "total_cost": float(total_cost),
        "total_net": float(total_net),
        "total_steam_sell": float(total_steam_sell),
        "total_qty": int(total_qty),
        "ratio": float(ratio),
        "discount": float(discount),
        "my_currency": current_my_currency,
        "my_currency_symbol": current_my_currency_symbol
    }

    _stats_cache.set(response_data)
    return response_data