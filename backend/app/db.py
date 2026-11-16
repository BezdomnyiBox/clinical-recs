from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db() -> None:
    """Apply all pending Alembic revisions before the API starts serving requests."""
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    command.upgrade(Config(str(config_path)), "head")


def get_session():
    with SessionLocal() as s:
        yield s


def to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
