import sqlite3
import json
from typing import Optional, List, Dict, Any
from config import DB_PATH, DATA_DIR
import os


class Migration:
    def __init__(self, version: int, name: str, up_sql: str, down_sql: Optional[str] = None, check_old_structure=None):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.check_old_structure = check_old_structure


class MigrationManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.migrations: List[Migration] = []
        self._init_migrations_table()

    def _init_migrations_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

    def register(self, migration: Migration):
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)

    def get_applied_versions(self) -> List[int]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] for row in cursor.fetchall()]

    def migrate(self):
        applied = set(self.get_applied_versions())
        
        for migration in self.migrations:
            if migration.version not in applied:
                print(f"Applying migration {migration.version}: {migration.name}")
                
                # 如果有检查函数且返回 False，则跳过迁移
                if migration.check_old_structure and not migration.check_old_structure():
                    print(f"  ⊘ Migration {migration.version} skipped (old structure not detected)")
                    # 标记为已应用，避免重复检查
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                            (migration.version, migration.name)
                        )
                    continue
                
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("BEGIN TRANSACTION")
                        try:
                            conn.executescript(migration.up_sql)
                            conn.execute(
                                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                                (migration.version, migration.name)
                            )
                            conn.commit()
                            print(f"  ✓ Migration {migration.version} applied successfully")
                        except Exception as e:
                            conn.rollback()
                            raise e
                except Exception as e:
                    print(f"  ✗ Migration {migration.version} failed: {e}")
                    raise

    def rollback(self, version: int):
        applied = self.get_applied_versions()
        if version not in applied:
            print(f"Version {version} is not applied")
            return

        for migration in reversed(self.migrations):
            if migration.version == version and migration.down_sql:
                print(f"Rolling back migration {migration.version}: {migration.name}")
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("BEGIN TRANSACTION")
                        try:
                            conn.executescript(migration.down_sql)
                            conn.execute(
                                "DELETE FROM schema_migrations WHERE version = ?",
                                (version,)
                            )
                            conn.commit()
                            print(f"  ✓ Rollback {migration.version} completed")
                        except Exception as e:
                            conn.rollback()
                            raise e
                except Exception as e:
                    print(f"  ✗ Rollback {migration.version} failed: {e}")
                    raise


def get_migration_manager() -> MigrationManager:
    manager = MigrationManager()

    def check_old_table_structure() -> bool:
        """检测是否是旧表结构"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute("PRAGMA table_info(history)")
                columns = [row[1] for row in cursor.fetchall()]
                return 'sell_currency' in columns
        except:
            return False

    manager.register(Migration(
        version=1,
        name="Optimize history table structure",
        up_sql="""
        -- 备份现有数据
        CREATE TABLE IF NOT EXISTS history_backup AS SELECT * FROM history;

        -- 创建新的 history 表结构
        CREATE TABLE IF NOT EXISTS history_new (
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
            discount REAL NOT NULL DEFAULT 0,
            ratio REAL NOT NULL DEFAULT 0,
            -- 设置快照（JSON格式）
            settings_snapshot TEXT,
            -- 计算结果快照（JSON格式）
            calculation_snapshot TEXT,
            -- 创建时间
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- 迁移数据
        INSERT INTO history_new (
            ts, item_name, note, unit_cost, unit_steam_sell, qty,
            unit_net, total_cost, total_steam_sell, total_net, discount, ratio,
            settings_snapshot, calculation_snapshot
        )
        SELECT 
            ts, item_name, note, unit_cost, unit_steam_sell, qty,
            unit_net, total_cost, total_steam_sell, total_net, discount, ratio,
            json_object(
                'sell_currency', sell_currency,
                'buy_currency', buy_currency,
                'my_currency', my_currency,
                'exchange_rate', exchange_rate,
                'steam_fee_rate', 0.15
            ),
            json_object(
                'total_cost_in_my_currency', total_cost_in_my_currency,
                'total_net_in_my_currency', total_net_in_my_currency,
                'total_steam_sell_in_my_currency', total_steam_sell_in_my_currency
            )
        FROM history;

        -- 删除旧表
        DROP TABLE history;

        -- 重命名新表
        ALTER TABLE history_new RENAME TO history;

        -- 重建索引
        CREATE INDEX IF NOT EXISTS idx_history_id_desc ON history(id DESC);
        CREATE INDEX IF NOT EXISTS idx_history_ts_desc ON history(ts DESC);
        """,
        down_sql="""
        -- 恢复旧表结构
        CREATE TABLE IF NOT EXISTS history_old (
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
            discount REAL NOT NULL DEFAULT 0,
            ratio REAL NOT NULL DEFAULT 0
        );

        -- 从备份恢复数据
        INSERT INTO history_old
        SELECT * FROM history_backup;

        -- 删除新表
        DROP TABLE history;

        -- 恢复旧表
        ALTER TABLE history_old RENAME TO history;

        -- 重建索引
        CREATE INDEX IF NOT EXISTS idx_history_id_desc ON history(id DESC);
        CREATE INDEX IF NOT EXISTS idx_history_ts_desc ON history(ts DESC);
        """,
        check_old_structure=check_old_table_structure
    ))

    def check_settings_without_last_fields() -> bool:
        """检测 settings 表是否没有 last_item_name 等字段"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute("PRAGMA table_info(settings)")
                columns = [row[1] for row in cursor.fetchall()]
                return 'last_item_name' not in columns
        except:
            return False

    manager.register(Migration(
        version=2,
        name="Add last input fields to settings table",
        up_sql="""
        ALTER TABLE settings ADD COLUMN last_item_name TEXT;
        ALTER TABLE settings ADD COLUMN last_unit_cost REAL;
        ALTER TABLE settings ADD COLUMN last_unit_sell REAL;
        """,
        check_old_structure=check_settings_without_last_fields
    ))

    def check_amount_columns_are_real() -> bool:
        """检测 history 表的金额列是否为 REAL（旧结构）"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute("PRAGMA table_info(history)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
                return columns.get("unit_cost", "TEXT") == "REAL"
        except:
            return False

    manager.register(Migration(
        version=3,
        name="Convert history amount columns from REAL to TEXT for Decimal precision",
        up_sql="""
        CREATE TABLE IF NOT EXISTS history_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            item_name TEXT NOT NULL,
            note TEXT,
            unit_cost TEXT NOT NULL,
            unit_steam_sell TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_net TEXT NOT NULL,
            total_cost TEXT NOT NULL,
            total_steam_sell TEXT NOT NULL,
            total_net TEXT NOT NULL,
            discount TEXT NOT NULL DEFAULT 0,
            ratio TEXT NOT NULL DEFAULT 0,
            settings_snapshot TEXT,
            calculation_snapshot TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        INSERT INTO history_new (
            id, ts, item_name, note, unit_cost, unit_steam_sell, qty,
            unit_net, total_cost, total_steam_sell, total_net, discount, ratio,
            settings_snapshot, calculation_snapshot, created_at
        )
        SELECT
            id, ts, item_name, note,
            CAST(unit_cost AS TEXT), CAST(unit_steam_sell AS TEXT), qty,
            CAST(unit_net AS TEXT), CAST(total_cost AS TEXT), CAST(total_steam_sell AS TEXT), CAST(total_net AS TEXT),
            CAST(discount AS TEXT), CAST(ratio AS TEXT),
            settings_snapshot, calculation_snapshot, created_at
        FROM history;

        DROP TABLE history;

        ALTER TABLE history_new RENAME TO history;

        CREATE INDEX IF NOT EXISTS idx_history_id_desc ON history(id DESC);
        CREATE INDEX IF NOT EXISTS idx_history_ts_desc ON history(ts DESC);
        """,
        check_old_structure=check_amount_columns_are_real
    ))

    return manager


if __name__ == "__main__":
    manager = get_migration_manager()
    manager.migrate()