from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _get_effective_db_url() -> str:
    db_url = settings.database_url
    if "@postgres:5432" in db_url:
        try:
            import socket
            socket.gethostbyname("postgres")
        except socket.gaierror:
            db_url = db_url.replace("@postgres:5432", "@127.0.0.1:5434")
    return db_url

db_url = _get_effective_db_url()

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
