"""Run Alembic migrations at startup, adopting databases created before migrations existed."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parent.parent


def upgrade_to_head(engine: Engine) -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        tables = set(inspect(conn).get_table_names())
        if "applications" in tables and "alembic_version" not in tables:
            # Created by the old create_all(): it matches the baseline schema.
            command.stamp(cfg, "0001")
        command.upgrade(cfg, "head")
