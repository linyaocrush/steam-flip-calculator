from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import threading
import time
from datetime import datetime
import requests
from contextlib import AbstractContextManager

app = Flask(__name__)
CORS(app)

DB_PATH = "steam_flip.db"

# 内存缓存机制
_settings_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 5  # 5秒缓存时间
}

_stats_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 5   # 5秒缓存时间
}

# 缓存清除函数
def invalidate_settings_cache():
    _settings_cache["data"] = None
    _settings_cache["timestamp"] = 0

def invalidate_stats_cache():
    _stats_cache["data"] = None
    _stats_cache["timestamp"] = 0

def check_cache_valid(cache_entry):
    """检查缓存是否有效"""
    if cache_entry["data"] is None:
        return False
    elapsed = time.time() - cache_entry["timestamp"]
    return elapsed < cache_entry["ttl"]


# 线程本地存储 - 每个线程有自己的数据库连接
_thread_local_db = threading.local()


class DatabaseConnection:
    """数据库连接上下文管理器，用于连接池管理"""

    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 注意：不在这里关闭连接，连接会被线程复用
        # 只提交事务，如果发生异常则回滚
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()


class ThreadLocalDatabaseConnection(AbstractContextManager):
    """线程本地数据库连接管理器"""

    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()


def get_db_connection():
    """获取数据库连接，使用线程本地存储实现连接池"""
    conn = getattr(_thread_local_db, 'connection', None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _thread_local_db.connection = conn
    return conn


def close_db_connection(e=None):
    """关闭数据库连接（在请求结束时调用）"""
    conn = getattr(_thread_local_db, 'connection', None)
    if conn is not None:
        conn.close()
        _thread_local_db.connection = None


def with_db_transaction(func):
    """数据库事务装饰器"""
    def wrapper(*args, **kwargs):
        conn = get_db_connection()
        try:
            result = func(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
    return wrapper


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
            total_net REAL NOT NULL
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

    # 创建 history 表索引以提升查询性能
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_id_desc ON history(id DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_ts_desc ON history(ts DESC)")
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


init_db()


# 注册请求生命周期钩子
@app.teardown_request
def teardown_db_connection(exception=None):
    """请求结束时关闭数据库连接"""
    close_db_connection(exception)


@app.route("/api/calculate", methods=["POST"])
def calculate():
    data = request.json
    unit_cost = float(data.get("unit_cost", 0))
    unit_steam_sell = float(data.get("unit_steam_sell", 0))
    qty = int(data.get("qty", 1))
    use_exchange = data.get("use_exchange", False)
    exchange_rate = float(data.get("exchange_rate", 1.0))
    fee_rate = float(data.get("fee_rate", 0.15))
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

    return jsonify({
        "unit_net": unit_net,
        "total_cost": total_cost,
        "total_net": total_net,
        "total_steam_sell": total_steam_sell,
        "ratio": ratio,
        "discount": discount,
        "need_sell": need_sell
    })


def get_exchange_rate_cached(base, target, force_refresh=False):
    """获取汇率，支持12小时缓存"""
    if base == target:
        return 1.0, None, "相同货币"
    
    conn = get_db_connection()
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
            from datetime import datetime
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
        
        cur.execute(
            "UPDATE settings SET exchange_rate = ?, exchange_rate_updated_at = ? WHERE id = 1",
            (rate, updated_at)
        )
        conn.commit()

        # 汇率变更后清除设置缓存（因为汇率是设置的一部分）
        invalidate_settings_cache()

        return rate, updated_at, "获取成功"
    except Exception as e:
        return cached_rate or 1.0, cached_time, f"获取失败: {str(e)}"


@app.route("/api/settings", methods=["GET"])
def get_settings():
    # 检查缓存是否有效
    if check_cache_valid(_settings_cache):
        return _settings_cache["data"]

    conn = get_db_connection()
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

    # 缓存响应结果
    _settings_cache["data"] = jsonify(response_data)
    _settings_cache["timestamp"] = time.time()

    return _settings_cache["data"]


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json
    buy_currency = data.get("buy_currency", "CNY").strip()
    buy_currency_symbol = data.get("buy_currency_symbol", "¥").strip()
    sell_currency = data.get("sell_currency", "CNY").strip()
    sell_currency_symbol = data.get("sell_currency_symbol", "¥").strip()
    exchange_rate = float(data.get("exchange_rate", 1.0))
    steam_fee_rate = float(data.get("steam_fee_rate", 0.15))
    theme_mode = data.get("theme_mode", "LIGHT").strip()
    my_currency = data.get("my_currency", "CNY").strip()
    my_currency_symbol = data.get("my_currency_symbol", "¥").strip()
    language = data.get("language", "zh").strip()

    if not buy_currency:
        return jsonify({"error": "买入货币不能为空"}), 400
    if not sell_currency:
        return jsonify({"error": "卖出货币不能为空"}), 400
    if steam_fee_rate < 0 or steam_fee_rate >= 1:
        return jsonify({"error": "手续费率必须在 0 到 1 之间"}), 400
    if theme_mode not in ["LIGHT", "DARK"]:
        return jsonify({"error": "主题模式必须是 LIGHT 或 DARK"}), 400
    if not my_currency:
        return jsonify({"error": "我的货币不能为空"}), 400
    if language not in ["zh", "en", "ja"]:
        return jsonify({"error": "语言设置必须是 zh、en 或 ja"}), 400

    conn = get_db_connection()
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

    conn = get_db_connection()
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
    conn.commit()

    # 设置变更后清除缓存
    invalidate_settings_cache()
    invalidate_stats_cache()  # 设置变更可能影响历史记录的统计计算

    return jsonify({
        "message": "设置已保存",
        "auto_fetch_rate": auto_fetch_rate,
        "rate_source": rate_source,
        "exchange_rate": exchange_rate,
        "exchange_rate_updated_at": updated_at
    }), 200


@app.route("/api/records", methods=["GET"])
def get_records():
    """优化查询：只选择前端需要的字段，减少数据传输量"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, ts, item_name, note, unit_cost, unit_steam_sell,
               qty, total_cost, total_net, discount
        FROM (
            SELECT id, ts, item_name, COALESCE(note, '') as note,
                   unit_cost, unit_steam_sell, qty, total_cost, total_net,
                   ROUND(100.0 * (1.0 - total_cost / total_net), 2) as discount
            FROM history
            ORDER BY id DESC
            LIMIT 500
        )
        ORDER BY id DESC  -- 外层再次排序确保顺序正确
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
            "total_cost": row["total_cost"],
            "total_net": row["total_net"],
            "discount_pct": row["discount"]  # 服务器计算折扣百分比，减少前端计算
        })
    return jsonify(records)


@app.route("/api/records", methods=["POST"])
def add_record():
    data = request.json
    item_name = data.get("item_name", "").strip()
    note = data.get("note", "").strip()
    unit_cost = float(data.get("unit_cost", 0))
    unit_steam_sell = float(data.get("unit_steam_sell", 0))
    qty = int(data.get("qty", 1))

    if not item_name:
        return jsonify({"error": "请填写物品名称"}), 400
    if unit_cost <= 0 or unit_steam_sell <= 0:
        return jsonify({"error": "单价必须大于 0"}), 400

    # 读取当前设置的手续费率，而不是写死的 0.15
    conn = get_db_connection()
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
    conn.commit()

    # 添加历史记录后清除统计缓存
    invalidate_stats_cache()

    return jsonify({"message": "已记录"}), 201


@app.route("/api/records/<int:record_id>", methods=["DELETE"])
def delete_record(record_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()

    # 删除历史记录后清除统计缓存
    invalidate_stats_cache()

    return jsonify({"message": "已删除"}), 200


@app.route("/api/records", methods=["DELETE"])
def clear_records():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM history")
    conn.commit()

    # 清空历史记录后清除统计缓存
    invalidate_stats_cache()

    return jsonify({"message": "已清空全部历史"}), 200


@app.route("/api/stats", methods=["GET"])
def get_stats():
    # 检查缓存是否有效
    if check_cache_valid(_stats_cache):
        return _stats_cache["data"]

    conn = get_db_connection()
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

    # 缓存响应结果
    _stats_cache["data"] = jsonify(response_data)
    _stats_cache["timestamp"] = time.time()

    return _stats_cache["data"]


@app.route("/api/exchange-rate", methods=["GET"])
def get_exchange_rate():
    base = request.args.get("base", "CNY")
    target = request.args.get("target", "CNY")
    
    if not base or not target:
        return jsonify({"error": "缺少参数：base 和 target"}), 400
    
    if base == target:
        return jsonify({"error": "买入货币和卖出货币相同，无需汇率"}), 400
    
    try:
        url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if target not in data.get("rates", {}):
            return jsonify({"error": f"无法获取 {base} 到 {target} 的汇率"}), 400
        
        rate = round(data["rates"][target], 4)
        return jsonify({
            "base": base,
            "target": target,
            "rate": rate
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"获取汇率失败：{str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"服务器错误：{str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)