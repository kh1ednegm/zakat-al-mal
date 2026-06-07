from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL
from database.models import Base


def get_engine():
    return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session() -> Session:
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
