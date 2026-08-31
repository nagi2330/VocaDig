"""Application entry point for early VocaDig phases."""

from backend.database.database import create_database, create_session_factory
from backend.settings import load_settings


def create_application(database_url: str | None = None) -> None:
    """Initialize the local database used by the backend."""
    database_url = database_url or load_settings().database.url
    session_factory = create_session_factory(database_url)
    create_database(session_factory.kw["bind"])


if __name__ == "__main__":
    create_application()
    print("VocaDig backend initialized.")