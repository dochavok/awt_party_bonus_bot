"""Alembic's environment (DB-4).

The bot runs migrations on a connection it has already opened
(``config.attributes["connection"]``). From the command line, the maintainer runs
``uv run alembic upgrade head`` in the project folder, which uses ``DATABASE_URL``
(DB-1).
"""

from alembic import context
from sqlalchemy import Connection, create_engine

from awt_bonus.schema import metadata
from awt_bonus.settings import Environment


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    _run(connection)
else:
    url = Environment().database_url.replace("+aiosqlite", "")
    with create_engine(url).connect() as own_connection:
        _run(own_connection)
