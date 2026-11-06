"""Exercise all migrations in isolated PostgreSQL temporary tables, then roll back."""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from .database import engine


def verify():
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("SET LOCAL search_path TO pg_temp,public"))
            connection.execute(
                text("CREATE TEMP TABLE migration_probe (id integer) ON COMMIT DROP")
            )
            schema = connection.scalar(text("SELECT current_schema()"))
            config = Config("alembic.ini")
            config.attributes.update(connection=connection, version_table_schema=schema)
            command.upgrade(config, "head")
            inspector = inspect(connection)
            assert {
                "documents",
                "chunks",
                "sessions",
                "messages",
                "retrieval_logs",
            } <= set(inspector.get_temp_table_names())
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0004"
            )
            assert "is_system" in {
                c["name"] for c in inspector.get_columns("documents", schema=schema)
            }
            assert "uq_messages_session_sequence" in {
                c["name"]
                for c in inspector.get_unique_constraints("messages", schema=schema)
            }
        finally:
            transaction.rollback()
    print("Fresh migration chain verified; temporary tables rolled back.")


if __name__ == "__main__":
    verify()
