import requests
from datetime import datetime
from database import get_db, invalidate_settings_cache


def fetch_exchange_rate(base: str, target: str, force_refresh: bool = False) -> tuple:
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