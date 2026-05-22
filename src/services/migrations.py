import sqlite3
from typing import Optional, List, Callable
from config import DB_PATH


class Migration:
    def __init__(self, version: int, name: str,
                 up_sql: Optional[str] = None,
                 up_fn: Optional[Callable] = None):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.up_fn = up_fn


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
                with sqlite3.connect(self.db_path) as conn:
                    try:
                        conn.execute("BEGIN TRANSACTION")
                        if migration.up_fn:
                            migration.up_fn(conn)
                        elif migration.up_sql:
                            conn.executescript(migration.up_sql)
                        conn.execute(
                            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                            (migration.version, migration.name)
                        )
                        conn.commit()
                        print(f"  v Migration {migration.version} applied successfully")
                    except Exception as e:
                        conn.rollback()
                        print(f"  x Migration {migration.version} failed: {e}")
                        raise


def _columns(conn, table: str) -> dict:
    """Return {column_name: type} for a table."""
    cursor = conn.execute("PRAGMA table_info(%s)" % table)
    return {row[1]: row[2] for row in cursor.fetchall()}


def get_migration_manager() -> MigrationManager:
    manager = MigrationManager()

    # --- v1: Optimize history table structure ---
    def up_v1(conn):
        cols = _columns(conn, "history")
        if 'sell_currency' not in cols:
            return  # Already new structure, nothing to do

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS history_backup AS SELECT * FROM history;

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
                settings_snapshot TEXT,
                calculation_snapshot TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

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

            DROP TABLE history;
            ALTER TABLE history_new RENAME TO history;

            CREATE INDEX IF NOT EXISTS idx_history_id_desc ON history(id DESC);
            CREATE INDEX IF NOT EXISTS idx_history_ts_desc ON history(ts DESC);
        """)

    manager.register(Migration(version=1, name="Optimize history table structure", up_fn=up_v1))

    # --- v2: Add last input fields to settings table ---
    def up_v2(conn):
        cols = _columns(conn, "settings")
        if 'last_item_name' in cols:
            return  # Already has the columns
        conn.executescript("""
            ALTER TABLE settings ADD COLUMN last_item_name TEXT;
            ALTER TABLE settings ADD COLUMN last_unit_cost REAL;
            ALTER TABLE settings ADD COLUMN last_unit_sell REAL;
        """)

    manager.register(Migration(version=2, name="Add last input fields to settings table", up_fn=up_v2))

    # --- v3: Convert history amount columns from REAL to TEXT ---
    def up_v3(conn):
        cols = _columns(conn, "history")
        if cols.get("unit_cost", "TEXT") != "REAL":
            return  # Already TEXT
        # Ensure ratio column exists before the conversion SELECT
        if 'ratio' not in cols:
            conn.execute("ALTER TABLE history ADD COLUMN ratio REAL NOT NULL DEFAULT 0")
        conn.executescript("""
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
        """)

    manager.register(Migration(version=3, name="Convert history amount columns to TEXT for Decimal", up_fn=up_v3))

    # --- v4: Add ratio column to history (for pre-v1 schemas that skipped the migration) ---
    # This covers databases created before the ratio column was added to the schema.
    def up_v4(conn):
        cols = _columns(conn, "history")
        if 'ratio' in cols:
            return
        conn.execute("ALTER TABLE history ADD COLUMN ratio REAL NOT NULL DEFAULT 0")

    manager.register(Migration(version=4, name="Add ratio column to history table", up_fn=up_v4))

    return manager


if __name__ == "__main__":
    manager = get_migration_manager()
    manager.migrate()
