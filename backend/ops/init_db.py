"""Initialize application tables using an existing pgvector extension."""

from sqlalchemy import text

from ..core.database import Base, engine


def initialize():
    with engine.begin() as conn:
        installed = conn.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        if not installed:
            database = conn.scalar(text("SELECT current_database()"))
            raise RuntimeError(
                f"pgvector is not enabled in database {database!r}. "
                "A database administrator must enable CREATE EXTENSION vector in this database. "
                "Installing server files or enabling it in another database is insufficient."
            )
        Base.metadata.create_all(conn)


if __name__ == "__main__":
    initialize()
