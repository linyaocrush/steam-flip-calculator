import time
import requests
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from services.database import get_db, invalidate_settings_cache

_exchange_rate_cache = {}
_CACHE_TTL = 300  # 5 minutes in-memory cache


def _get_cached_rate(base: str, target: str):
    key = (base, target)
    entry = _exchange_rate_cache.get(key)
    if entry and time.time() - entry["timestamp"] < _CACHE_TTL:
        return entry["rate"], entry["updated_at"]
    return None


def _set_cached_rate(base: str, target: str, rate: float, updated_at: str):
    key = (base, target)
    _exchange_rate_cache[key] = {"rate": rate, "updated_at": updated_at, "timestamp": time.time()}


def fetch_exchange_rate(base: str, target: str, force_refresh: bool = False) -> tuple:
    if base == target:
        return 1.0, None, "相同货币"

    if not force_refresh:
        cached = _get_cached_rate(base, target)
        if cached:
            return cached[0], cached[1], "使用内存缓存"

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT rate, updated_at FROM exchange_rates WHERE base_currency = ? AND target_currency = ?",
            (base, target)
        )
        row = cur.fetchone()

        cached_rate = None
        cached_time = None
        if row:
            cached_rate = float(row["rate"])
            cached_time = row["updated_at"]

        if not force_refresh and cached_rate is not None and cached_time is not None:
            try:
                cached_datetime = datetime.strptime(cached_time, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                diff_hours = (now - cached_datetime).total_seconds() / 3600
                if diff_hours < 12:
                    _set_cached_rate(base, target, cached_rate, cached_time)
                    return cached_rate, cached_time, "使用DB缓存"
            except Exception:
                pass
    
    try:
        url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if target not in data.get("rates", {}):
            return cached_rate or 1.0, cached_time, "获取失败，使用缓存"
        
        rate_decimal = Decimal(str(data["rates"][target]))
        rate = float(rate_decimal.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _set_cached_rate(base, target, rate, updated_at)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO exchange_rates (base_currency, target_currency, rate, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(base_currency, target_currency) 
                DO UPDATE SET rate = excluded.rate, updated_at = excluded.updated_at
                """,
                (base, target, rate, updated_at)
            )
        
        return rate, updated_at, "获取成功"
    except Exception as e:
        return cached_rate or 1.0, cached_time, f"获取失败: {str(e)}"