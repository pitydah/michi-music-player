"""E2E test: full migration cycle."""
import sqlite3
from library.schema import Schema
from library.migrations import migrate, rollback
def test_e2e_migration_cycle():
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    migrate(conn)
    rollback(conn, 1)
    migrate(conn)
    conn.close()
