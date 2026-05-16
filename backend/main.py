from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import List
import requests
from datetime import datetime

from schemas import (
    CalculateRequest, CalculateResponse,
    SettingsRequest, SettingsResponse, SettingsSaveResponse,
    RecordRequest, RecordResponse,
    StatsResponse, ErrorResponse, ExchangeRateResponse
)
from database import (
    get_db, init_db,
    _settings_cache, _stats_cache,
    invalidate_settings_cache, invalidate_stats_cache,
    get_exchange_rate_cached
)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail["error"]}
        )
    elif isinstance(exc.detail, str):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail)}
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": f"请求参数验证失败: {str(exc.errors())}"}
    )


@app.on_event("startup")
def startup_event():
    init_db()


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
                "exchange_rate_updated_at": row["exchange_rate_updated_at"],
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
                "exchange_rate_updated_at": None,
                "language": "zh"
            }

    _settings_cache.set(response_data)
    return response_data


@app.post("/api/settings", response_model=SettingsSaveResponse)
def save_settings(data: SettingsRequest):
    buy_currency = data.buy_currency.strip()
    buy_currency_symbol = data.buy_currency_symbol.strip()
    sell_currency = data.sell_currency.strip()
    sell_currency_symbol = data.sell_currency_symbol.strip()
    exchange_rate = data.exchange_rate
    steam_fee_rate = data.steam_fee_rate
    theme_mode = data.theme_mode.strip()
    my_currency = data.my_currency.strip()
    my_currency_symbol = data.my_currency_symbol.strip()
    language = data.language.strip()

    if not buy_currency:
        raise HTTPException(status_code=400, detail="买入货币不能为空")
    if not sell_currency:
        raise HTTPException(status_code=400, detail="卖出货币不能为空")
    if steam_fee_rate < 0 or steam_fee_rate >= 1:
        raise HTTPException(status_code=400, detail="手续费率必须在 0 到 1 之间")
    if theme_mode not in ["LIGHT", "DARK"]:
        raise HTTPException(status_code=400, detail="主题模式必须是 LIGHT 或 DARK")
    if not my_currency:
        raise HTTPException(status_code=400, detail="我的货币不能为空")
    if language not in ["zh", "en", "ja"]:
        raise HTTPException(status_code=400, detail="语言设置必须是 zh、en 或 ja")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT exchange_rate_updated_at FROM settings WHERE id = 1")
        row = cur.fetchone()
        current_updated_at = row["exchange_rate_updated_at"] if row else None

    auto_fetch_rate = False
    rate_source = "用户输入"
    updated_at = current_updated_at

    if buy_currency == sell_currency:
        exchange_rate = 1.0
        updated_at = None

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
                exchange_rate_updated_at = ?,
                language = ?
            WHERE id = 1
            """,
            (buy_currency, buy_currency_symbol, sell_currency,
             sell_currency_symbol, exchange_rate, steam_fee_rate,
             theme_mode, my_currency, my_currency_symbol, updated_at, language)
        )

    invalidate_settings_cache()
    invalidate_stats_cache()

    return {
        "message": "设置已保存",
        "auto_fetch_rate": auto_fetch_rate,
        "rate_source": rate_source,
        "exchange_rate": exchange_rate,
        "exchange_rate_updated_at": updated_at
    }


@app.get("/api/records", response_model=List[RecordResponse])
def get_records():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ts, item_name, note, unit_cost, unit_steam_sell,
                   qty, unit_net, total_cost, total_net, discount
            FROM (
                SELECT id, ts, item_name, COALESCE(note, '') as note,
                       unit_cost, unit_steam_sell, qty, unit_net, total_cost, total_net,
                       ROUND(100.0 * (1.0 - total_cost / total_net), 2) as discount
                FROM history
                ORDER BY id DESC
                LIMIT 500
            )
            ORDER BY id DESC
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
            "discount_pct": row["discount"]
        })
    return records


@app.post("/api/records", status_code=status.HTTP_201_CREATED)
def add_record(data: RecordRequest):
    item_name = data.item_name.strip()
    note = data.note.strip()
    unit_cost = data.unit_cost
    unit_steam_sell = data.unit_steam_sell
    qty = data.qty

    if not item_name:
        raise HTTPException(status_code=400, detail="请填写物品名称")
    if unit_cost <= 0 or unit_steam_sell <= 0:
        raise HTTPException(status_code=400, detail="单价必须大于 0")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT steam_fee_rate FROM settings WHERE id = 1")
        row = cur.fetchone()
        fee_rate = row["steam_fee_rate"] if row else 0.15
        net_rate = 1.0 - fee_rate

        unit_net = unit_steam_sell * net_rate
        total_cost = unit_cost * qty
        total_steam_sell = unit_steam_sell * qty
        total_net = unit_net * qty
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            """
            INSERT INTO history (ts, item_name, note, unit_cost, unit_steam_sell,
                                qty, unit_net, total_cost, total_steam_sell, total_net)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, item_name, note, unit_cost, unit_steam_sell, qty,
             unit_net, total_cost, total_steam_sell, total_net),
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

    ratio = (total_cost / total_net) if total_net > 0 else 0.0
    discount = (1.0 - ratio) if total_net > 0 else 0.0

    response_data = {
        "total_cost": float(total_cost),
        "total_net": float(total_net),
        "total_steam_sell": float(total_steam_sell),
        "total_qty": int(total_qty),
        "ratio": float(ratio),
        "discount": float(discount)
    }

    _stats_cache.set(response_data)
    return response_data


@app.get("/api/exchange-rate", response_model=ExchangeRateResponse)
def get_exchange_rate(base: str = "CNY", target: str = "CNY"):
    if not base or not target:
        raise HTTPException(status_code=400, detail="缺少参数：base 和 target")
    
    if base == target:
        raise HTTPException(status_code=400, detail="买入货币和卖出货币相同，无需汇率")
    
    try:
        url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if target not in data.get("rates", {}):
            raise HTTPException(status_code=400, detail=f"无法获取 {base} 到 {target} 的汇率")
        
        rate = round(data["rates"][target], 4)
        return {
            "base": base,
            "target": target,
            "rate": rate
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"获取汇率失败：{str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误：{str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)