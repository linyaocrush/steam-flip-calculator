from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import contextmanager
import sqlite3
import threading
import time
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class CalculateRequest(BaseModel):
    unit_cost: float = Field(default=0.0, description="第三方成本（单价）")
    unit_steam_sell: float = Field(default=0.0, description="Steam 售出金额（单价）")
    qty: int = Field(default=1, description="数量")
    use_exchange: bool = Field(default=False, description="是否使用汇率转换")
    exchange_rate: float = Field(default=1.0, description="汇率")
    fee_rate: float = Field(default=0.15, description="手续费率")

class CalculateResponse(BaseModel):
    unit_net: float
    total_cost: float
    total_net: float
    total_steam_sell: float
    ratio: float
    discount: float
    need_sell: float

class SettingsRequest(BaseModel):
    buy_currency: str = Field(default="CNY", description="买入货币")
    buy_currency_symbol: str = Field(default="¥", description="买入货币符号")
    sell_currency: str = Field(default="CNY", description="卖出货币")
    sell_currency_symbol: str = Field(default="¥", description="卖出货币符号")
    exchange_rate: float = Field(default=1.0, description="汇率")
    steam_fee_rate: float = Field(default=0.15, description="Steam 手续费率")
    theme_mode: str = Field(default="LIGHT", description="主题模式")
    my_currency: str = Field(default="CNY", description="我的货币")
    my_currency_symbol: str = Field(default="¥", description="我的货币符号")
    language: str = Field(default="zh", description="语言")

class SettingsResponse(BaseModel):
    buy_currency: str
    buy_currency_symbol: str
    sell_currency: str
    sell_currency_symbol: str
    exchange_rate: float
    steam_fee_rate: float
    theme_mode: str
    my_currency: str
    my_currency_symbol: str
    language: str

class RecordRequest(BaseModel):
    item_name: str = Field(..., description="物品名称")
    note: str = Field(default="", description="备注")
    unit_cost: float = Field(..., description="成本单价")
    unit_steam_sell: float = Field(..., description="Steam 售价单价")
    qty: int = Field(default=1, description="数量")
    discount: float = Field(default=0.0, description="折扣值（从计算器页面传入）")

class RecordResponse(BaseModel):
    id: int
    ts: str
    item_name: str
    note: str
    unit_cost: float
    unit_steam_sell: float
    qty: int
    unit_net: float
    total_cost: float
    total_net: float
    discount: float

class StatsResponse(BaseModel):
    total_cost: float
    total_net: float
    total_steam_sell: float
    total_qty: int
    ratio: float
    discount: float
    my_currency: str = Field(default="CNY", description="我的货币代码")
    my_currency_symbol: str = Field(default="¥", description="我的货币符号")

class ExchangeRateResponse(BaseModel):
    rate: float
    updated_at: str
    message: str

@app.post("/api/calculate", response_model=CalculateResponse)
def calculate(data: CalculateRequest):
    unit_cost = data.unit_cost
    unit_steam_sell = data.unit_steam_sell
    qty = data.qty
    use_exchange = data.use_exchange
    exchange_rate = data.exchange_rate
    fee_rate = data.fee_rate
    net_rate = 1.0 - fee_rate

    unit_net = unit_steam_sell * net_rate
    
    if use_exchange:
        total_cost = unit_cost * qty * exchange_rate
    else:
        total_cost = unit_cost * qty
        
    total_net = unit_net * qty
    total_steam_sell = unit_steam_sell * qty

    ratio = (total_cost / total_net) if total_net > 0 else 0.0
    discount = (1.0 - ratio) if total_net > 0 else 0.0
    
    if use_exchange:
        need_sell = (unit_cost * exchange_rate / net_rate) if net_rate > 0 else 0.0
    else:
        need_sell = (unit_cost / net_rate) if net_rate > 0 else 0.0

    return {
        "unit_net": unit_net,
        "total_cost": total_cost,
        "total_net": total_net,
        "total_steam_sell": total_steam_sell,
        "ratio": ratio,
        "discount": discount,
        "need_sell": need_sell
    }

@app.get("/api/settings", response_model=SettingsResponse)
def get_settings():
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
                "language": row["language"]
            }
        else:
            response_data = {
                "buy_currency": "CNY",
                "buy_currency_symbol": "¥",
                "sell_currency": "CNY",
                "sell_currency_symbol": "¥",
                "exchange_rate": 1.0,
                "steam_fee_rate": 0.15,
                "theme_mode": "LIGHT",
                "my_currency": "CNY",
                "my_currency_symbol": "¥",
                "language": "zh"
            }

    _settings_cache.set(response_data)
    return response_data

@app.post("/api/settings", response_model=SettingsResponse)
def save_settings(data: SettingsRequest):
    if data.buy_currency == data.sell_currency:
        raise HTTPException(status_code=400, detail="买入货币和卖出货币相同，无需汇率")
    if data.steam_fee_rate < 0 or data.steam_fee_rate > 1:
        raise HTTPException(status_code=400, detail="手续费率必须在 0-100% 之间")

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
                data.buy_currency,
                data.buy_currency_symbol,
                data.sell_currency,
                data.sell_currency_symbol,
                data.exchange_rate,
                data.steam_fee_rate,
                data.theme_mode,
                data.my_currency,
                data.my_currency_symbol,
                data.language
            )
        )

    invalidate_settings_cache()
    invalidate_stats_cache()

    return {
        "buy_currency": data.buy_currency,
        "buy_currency_symbol": data.buy_currency_symbol,
        "sell_currency": data.sell_currency,
        "sell_currency_symbol": data.sell_currency_symbol,
        "exchange_rate": data.exchange_rate,
        "steam_fee_rate": data.steam_fee_rate,
        "theme_mode": data.theme_mode,
        "my_currency": data.my_currency,
        "my_currency_symbol": data.my_currency_symbol,
        "language": data.language
    }

@app.get("/api/records")
def get_records():
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
            LIMIT 500
            """
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

    return {"records": records}

@app.post("/api/records")
def add_record(data: RecordRequest):
    item_name = data.item_name.strip()
    note = data.note.strip()
    unit_cost = data.unit_cost
    unit_steam_sell = data.unit_steam_sell
    qty = data.qty
    discount = data.discount  # 直接使用前端传入的折扣值

    if not item_name:
        raise HTTPException(status_code=400, detail="请填写物品名称")
    if unit_cost <= 0 or unit_steam_sell <= 0:
        raise HTTPException(status_code=400, detail="单价必须大于 0")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT steam_fee_rate, sell_currency, sell_currency_symbol, buy_currency, buy_currency_symbol, exchange_rate, my_currency, my_currency_symbol FROM settings WHERE id = 1")
        row = cur.fetchone()
        fee_rate = row["steam_fee_rate"] if row else 0.15
        sell_currency = row["sell_currency"] if row else "CNY"
        sell_currency_symbol = row["sell_currency_symbol"] if row else "¥"
        buy_currency = row["buy_currency"] if row else "CNY"
        buy_currency_symbol = row["buy_currency_symbol"] if row else "¥"
        exchange_rate = row["exchange_rate"] if row else 1.0
        my_currency = row["my_currency"] if row else "CNY"
        my_currency_symbol = row["my_currency_symbol"] if row else "¥"
        
        net_rate = 1.0 - fee_rate

        unit_net = unit_steam_sell * net_rate
        total_cost = unit_cost * qty
        total_steam_sell = unit_steam_sell * qty
        total_net = unit_net * qty
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        total_cost_in_my_currency = total_cost * exchange_rate
        total_net_in_my_currency = total_net * exchange_rate
        total_steam_sell_in_my_currency = total_steam_sell * exchange_rate
        
        # 直接使用前端传入的折扣值，不再重新计算
        # discount = data.discount  # 已在开头获取

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
            (ts, item_name, note, unit_cost, unit_steam_sell, qty,
             unit_net, total_cost, total_steam_sell, total_net,
             sell_currency, sell_currency_symbol,
             buy_currency, buy_currency_symbol,
             exchange_rate,
             my_currency, my_currency_symbol,
             total_cost_in_my_currency, total_net_in_my_currency,
             total_steam_sell_in_my_currency, discount),
        )

    invalidate_stats_cache()

    return {"message": "已记录"}

@app.delete("/api/records/{record_id}")
def delete_record(record_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM history WHERE id = ?", (record_id,))

    invalidate_stats_cache()

    return {"message": "已删除"}

@app.delete("/api/records")
def clear_records():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM history")

    invalidate_stats_cache()

    return {"message": "已清空全部历史"}

@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    if _stats_cache.is_valid():
        return _stats_cache.get()

    with get_db() as conn:
        cur = conn.cursor()
        
        # 获取当前设置
        cur.execute("SELECT my_currency, my_currency_symbol, exchange_rate, sell_currency FROM settings WHERE id = 1")
        settings_row = cur.fetchone()
        current_my_currency = settings_row["my_currency"] if settings_row else "CNY"
        current_my_currency_symbol = settings_row["my_currency_symbol"] if settings_row else "¥"
        current_exchange_rate = settings_row["exchange_rate"] if settings_row else 1.0
        current_sell_currency = settings_row["sell_currency"] if settings_row else "CNY"
        
        # 查询原始金额（按售出货币）
        cur.execute(
            """
            SELECT
                COALESCE(SUM(total_cost), 0),
                COALESCE(SUM(total_net), 0),
                COALESCE(SUM(total_steam_sell), 0),
                COALESCE(SUM(qty), 0)
            FROM history
            """
        )
        total_cost, total_net, total_steam_sell, total_qty = cur.fetchone()
        
        # 根据当前设置转换为我的货币
        if current_sell_currency != current_my_currency:
            total_cost = total_cost * current_exchange_rate
            total_net = total_net * current_exchange_rate
            total_steam_sell = total_steam_sell * current_exchange_rate

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

@app.get("/api/exchange-rate", response_model=ExchangeRateResponse)
def get_exchange_rate(base: str = "CNY", target: str = "CNY"):
    if not base or not target:
        raise HTTPException(status_code=400, detail="缺少参数：base 和 target")
    
    if base == target:
        return {"rate": 1.0, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": "相同货币"}
    
    try:
        import requests
        url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if target not in data.get("rates", {}):
            return {"rate": 1.0, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": "获取失败"}
        
        rate = round(data["rates"][target], 4)
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE settings SET exchange_rate = ?, exchange_rate_updated_at = ? WHERE id = 1",
                (rate, updated_at)
            )
        
        invalidate_settings_cache()
        
        return {"rate": rate, "updated_at": updated_at, "message": "获取成功"}
    except Exception as e:
        return {"rate": 1.0, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": f"获取失败: {str(e)}"}

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
    
    cur.execute("PRAGMA table_info(history)")
    history_columns = [col[1] for col in cur.fetchall()]
    if "sell_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN sell_currency TEXT NOT NULL DEFAULT 'CNY'")
    if "sell_currency_symbol" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN sell_currency_symbol TEXT NOT NULL DEFAULT '¥'")
    if "buy_currency" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN buy_currency TEXT NOT NULL DEFAULT 'CNY'")
    if "buy_currency_symbol" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN buy_currency_symbol TEXT NOT NULL DEFAULT '¥'")
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
    if "discount" not in history_columns:
        cur.execute("ALTER TABLE history ADD COLUMN discount REAL NOT NULL DEFAULT 0")
    
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

@app.on_event("startup")
async def startup_event():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)