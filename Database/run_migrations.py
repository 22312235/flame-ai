from database.migration_runner import (
    run_migrations,
    show_migration_status,
)


if __name__ == "__main__":

    run_migrations()

    show_migration_status()