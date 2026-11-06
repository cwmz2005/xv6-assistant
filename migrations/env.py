from alembic import context

from backend.database import Base, engine


def migrate(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table_schema=context.config.attributes.get("version_table_schema"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations():
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        migrate(supplied)
    else:
        with engine.connect() as connection:
            migrate(connection)


run_migrations()
