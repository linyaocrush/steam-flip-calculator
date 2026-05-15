from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = "steam_flip.db"
FEE_RATE = 0.15
NET_RATE = 1.0 - FEE_RATE


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
    conn.commit()
    conn.close()


init_db()


@app.route("/api/calculate", methods=["POST"])
def calculate():
    data = request.json
    unit_cost = float(data.get("unit_cost", 0))
    unit_steam_sell = float(data.get("unit_steam_sell", 0))
    qty = int(data.get("qty", 1))

    unit_net = unit_steam_sell * NET_RATE
    total_cost = unit_cost * qty
    total_net = unit_net * qty
    total_steam_sell = unit_steam_sell * qty

    ratio = (unit_cost / unit_net) if unit_net > 0 else 0.0
    discount = (1.0 - ratio) if unit_net > 0 else 0.0
    need_sell = (unit_cost / NET_RATE) if NET_RATE > 0 else 0.0

    return jsonify({
        "unit_net": unit_net,
        "total_cost": total_cost,
        "total_net": total_net,
        "total_steam_sell": total_steam_sell,
        "ratio": ratio,
        "discount": discount,
        "need_sell": need_sell
    })


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

    unit_net = unit_steam_sell * NET_RATE
    total_cost = unit_cost * qty
    total_steam_sell = unit_steam_sell * qty
    total_net = unit_net * qty
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cur = conn.cursor()
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