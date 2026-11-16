from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(
        engine
    )  # TODO: перейти на Alembic, когда схема стабилизируется


def get_session():
    with SessionLocal() as s:
        yield s


def to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
