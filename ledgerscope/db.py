"""DuckDB connection manager and migration runner."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import duckdb

import threading

from ledgerscope.errors import DatabaseError, ErrorContext
from ledgerscope.logging import get_logger

logger = get_logger(__name__)

_connection: Optional[duckdb.DuckDBPyConnection] = None
_local = threading.local()


def get_db_dir() -> Path:
    """Return (and create) the ~/.ledgerscope/ directory."""
    db_dir = Path.home() / ".ledgerscope"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def get_db_path() -> Path:
    """Return the path to the DuckDB database file."""
    return get_db_dir() / "ledgerscope.duckdb"


def get_connection(db_path: Optional[Path] = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Get or create a singleton DuckDB connection.

    Args:
        db_path: Optional override for the database path.
                 Pass `:memory:` string for in-memory databases (testing).
        read_only: Whether to open the connection in read-only mode for concurrency.
    """
    global _connection
    if db_path is None:
        db_path = get_db_path()

    if read_only:
        if not hasattr(_local, "conn"):
            logger.debug(f"Creating read-only connection to {db_path}")
            _local.conn = duckdb.connect(str(db_path), read_only=True)
        return _local.conn

    if _connection is not None:
        return _connection

    logger.info(f"Creating database connection to {db_path}")
    try:
        _connection = duckdb.connect(str(db_path), read_only=False)
        return _connection
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise DatabaseError(f"Failed to connect to database at {db_path}") from e


def reset_connection() -> None:
    """Close and reset the singleton connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def get_migrations_dir() -> Path:
    """Return the path to the migrations directory."""
    return Path(__file__).parent / "migrations"


def get_views_path() -> Path:
    """Return the path to the analytics views SQL file."""
    return Path(__file__).parent / "analytics" / "views.sql"


def run_migrations(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Apply unapplied SQL migrations in order.

    Tracks applied migrations in a `schema_migrations` table.
    Returns list of newly applied migration filenames.
    """
    # Ensure the tracking table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename VARCHAR PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Get already-applied migrations
    applied = {
        row[0]
        for row in conn.execute(
            "SELECT filename FROM schema_migrations"
        ).fetchall()
    }

    migrations_dir = get_migrations_dir()
    if not migrations_dir.exists():
        return []

    # Collect and sort migration files
    migration_files = sorted(
        f for f in migrations_dir.iterdir()
        if f.suffix == ".sql" and f.name not in applied
    )

    newly_applied = []
    for mig_file in migration_files:
        sql = mig_file.read_text(encoding="utf-8")
        conn.execute(sql)
        conn.execute(
            "INSERT INTO schema_migrations (filename) VALUES (?)",
            [mig_file.name],
        )
        newly_applied.append(mig_file.name)

    return newly_applied


def create_views(conn: duckdb.DuckDBPyConnection) -> None:
    """Execute the analytics views SQL file to create/replace all views."""
    views_path = get_views_path()
    if views_path.exists():
        sql = views_path.read_text(encoding="utf-8")
        # Split on semicolons and execute each statement
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(stmt)


def init_db(db_path: Optional[Path] = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Initialize the database: run migrations and create views.

    This is the main entry point called by every CLI command.
    """
    conn = get_connection(db_path, read_only)
    if not read_only:
        run_migrations(conn)
        create_views(conn)
    return conn
