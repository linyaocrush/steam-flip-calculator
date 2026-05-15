from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = "steam_flip.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
            steam_fee_rate REAL NOT NULL DEFAULT 0.15
        )
        """
    )
    cur.execute("SELECT COUNT(*) FROM settings")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO settings (id) VALUES (1)")
    conn.commit()
    conn.close()


init_db()


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


@app.route("/api/settings", methods=["GET"])
def get_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM settings WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "buy_currency": row["buy_currency"],
            "buy_currency_symbol": row["buy_currency_symbol"],
            "sell_currency": row["sell_currency"],
            "sell_currency_symbol": row["sell_currency_symbol"],
            "exchange_rate": row["exchange_rate"],
            "steam_fee_rate": row["steam_fee_rate"]
        })
    return jsonify({
        "buy_currency": "CNY",
        "buy_currency_symbol": "¥",
        "sell_currency": "CNY",
        "sell_currency_symbol": "¥",
        "exchange_rate": 1.0,
        "steam_fee_rate": 0.15
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json
    buy_currency = data.get("buy_currency", "CNY").strip()
    buy_currency_symbol = data.get("buy_currency_symbol", "¥").strip()
    sell_currency = data.get("sell_currency", "CNY").strip()
    sell_currency_symbol = data.get("sell_currency_symbol", "¥").strip()
    exchange_rate = float(data.get("exchange_rate", 1.0))
    steam_fee_rate = float(data.get("steam_fee_rate", 0.15))

    if not buy_currency:
        return jsonify({"error": "买入货币不能为空"}), 400
    if not sell_currency:
        return jsonify({"error": "卖出货币不能为空"}), 400
    if exchange_rate <= 0:
        return jsonify({"error": "汇率必须大于 0"}), 400
    if steam_fee_rate < 0 or steam_fee_rate >= 1:
        return jsonify({"error": "手续费率必须在 0 到 1 之间"}), 400

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
            steam_fee_rate = ?
        WHERE id = 1
        """,
        (buy_currency, buy_currency_symbol, sell_currency, 
         sell_currency_symbol, exchange_rate, steam_fee_rate)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "设置已保存"}), 200


@app.route("/api/records", methods=["GET"])
def get_records():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, ts, item_name, COALESCE(note, ''), unit_cost, unit_steam_sell, 
               qty, unit_net, total_cost, total_steam_sell, total_net
        FROM history
        ORDER BY id DESC
        LIMIT 500
        """
    )
    rows = cur.fetchall()
    conn.close()

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
            "total_steam_sell": row["total_steam_sell"],
            "total_net": row["total_net"]
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
    conn.close()

    return jsonify({"message": "已记录"}), 201


@app.route("/api/records/<int:record_id>", methods=["DELETE"])
def delete_record(record_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "已删除"}), 200


@app.route("/api/records", methods=["DELETE"])
def clear_records():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    return jsonify({"message": "已清空全部历史"}), 200


@app.route("/api/stats", methods=["GET"])
def get_stats():
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
    conn.close()

    ratio = (total_cost / total_net) if total_net > 0 else 0.0
    discount = (1.0 - ratio) if total_net > 0 else 0.0

    return jsonify({
        "total_cost": float(total_cost),
        "total_net": float(total_net),
        "total_steam_sell": float(total_steam_sell),
        "total_qty": int(total_qty),
        "ratio": float(ratio),
        "discount": float(discount)
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)