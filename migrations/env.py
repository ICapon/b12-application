from alembic import context

from app import models  # noqa: F401  (register tables)
from app.database import Base, make_engine

target_metadata = Base.metadata


def run_migrations() -> None:
    # Tests/startup may hand us an open connection; otherwise build one from DATABASE_URL.
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = make_engine()
    with engine.connect() as conn:
        _run(conn)


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite cannot ALTER most things in place
    )
    with context.begin_transaction():
        context.run_migrations()
    connection.commit()


run_migrations()
