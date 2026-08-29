from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import Base


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a session factory suitable for SQLite now and PostgreSQL later."""
    if database_url.startswith("sqlite:///"):
        database_path = Path(database_url.removeprefix("sqlite:///"))
        if database_path.parent != Path("."):
            database_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, future=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)