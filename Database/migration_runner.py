import hashlib
import re

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from database.connection import engine


# =========================================================
# Configuration
# =========================================================

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# PostgreSQL advisory lock identifier.
# Prevents multiple application instances from running
# migrations simultaneously.
MIGRATION_LOCK_ID = 847291


# =========================================================
# Migration Tracking Table
# =========================================================

CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


# =========================================================
# Migration Discovery
# =========================================================

def discover_migrations() -> list[Path]:
    """
    Finds SQL migration files and sorts them by filename.

    Example:
        001_initial_schema.sql
        002_document_tables.sql
    """

    if not MIGRATIONS_DIR.exists():
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration in migrations:
        if not re.match(r"^\d+_[a-zA-Z0-9_-]+\.sql$", migration.name):
            raise ValueError(
                f"Invalid migration filename: {migration.name}"
            )

    return migrations


# =========================================================
# Migration Utilities
# =========================================================

def get_migration_version(filename: str) -> str:
    """
    Extracts the version from a migration filename.

    Example:
        001_initial_schema.sql -> 001
    """

    return filename.split("_", 1)[0]


def calculate_checksum(content: str) -> str:
    """
    Generates a SHA-256 checksum of migration contents.

    This allows us to detect modifications to migrations
    that have already been applied.
    """

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# =========================================================
# Applied Migration Retrieval
# =========================================================

def get_applied_migrations(
    connection: Connection,
) -> dict[str, dict]:
    """
    Returns all migrations already applied to PostgreSQL.
    """

    result = connection.execute(
        text("""
            SELECT version, filename, checksum
            FROM schema_migrations
        """)
    )

    return {
        row.version: {
            "filename": row.filename,
            "checksum": row.checksum,
        }
        for row in result
    }


# =========================================================
# SQL Execution
# =========================================================

def execute_migration(
    connection: Connection,
    migration: Path,
) -> None:
    """
    Executes a migration SQL file.

    Uses Psycopg's cursor with prepare=False so that
    a migration can contain multiple SQL statements.
    """

    sql_content = migration.read_text(encoding="utf-8")

    raw_connection = connection.connection.driver_connection

    with raw_connection.cursor() as cursor:
        cursor.execute(sql_content, prepare=False)


# =========================================================
# Migration Runner
# =========================================================

def run_migrations() -> None:
    """
    Executes all pending migrations.

    Features:
        - Automatic migration discovery.
        - Ordered execution.
        - Duplicate execution prevention.
        - Checksum validation.
        - Transactional execution.
        - PostgreSQL advisory locking.
    """

    migrations = discover_migrations()

    if not migrations:
        print("No migration files found.")
        return

    print("Starting database migrations...")

    with engine.begin() as connection:

        # Prevent concurrent migration execution.
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": MIGRATION_LOCK_ID},
        )

        # Create migration tracking table.
        connection.execute(
            text(CREATE_MIGRATIONS_TABLE)
        )

        applied_migrations = get_applied_migrations(connection)

        for migration in migrations:

            filename = migration.name
            version = get_migration_version(filename)

            sql_content = migration.read_text(encoding="utf-8")
            checksum = calculate_checksum(sql_content)

            # Check whether this migration was already applied.
            if version in applied_migrations:

                previous = applied_migrations[version]

                if previous["filename"] != filename:
                    raise RuntimeError(
                        f"Migration version conflict: {version}"
                    )

                if previous["checksum"] != checksum:
                    raise RuntimeError(
                        f"Migration {filename} has been modified "
                        "after being applied. Create a new migration "
                        "instead of editing an existing one."
                    )

                print(f"[SKIPPED] {filename}")
                continue

            print(f"[RUNNING] {filename}")

            # Execute SQL statements.
            execute_migration(connection, migration)

            # Record successful execution.
            connection.execute(
                text("""
                    INSERT INTO schema_migrations (
                        version,
                        filename,
                        checksum
                    )
                    VALUES (
                        :version,
                        :filename,
                        :checksum
                    )
                """),
                {
                    "version": version,
                    "filename": filename,
                    "checksum": checksum,
                },
            )

            print(f"[SUCCESS] {filename}")

    print("Database migrations completed successfully.")


# =========================================================
# Migration Status
# =========================================================

def show_migration_status() -> None:
    """
    Displays applied and pending migrations.
    """

    migrations = discover_migrations()

    with engine.connect() as connection:

        table_exists = connection.execute(
            text("""
                SELECT to_regclass('public.schema_migrations')
            """)
        ).scalar()

        if table_exists is None:
            print("No migrations have been applied yet.")
            applied_migrations = {}
        else:
            applied_migrations = get_applied_migrations(connection)

    print("\nMigration status:")

    for migration in migrations:

        version = get_migration_version(migration.name)

        if version in applied_migrations:
            print(f"[APPLIED] {migration.name}")
        else:
            print(f"[PENDING] {migration.name}")