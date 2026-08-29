"""Application entry point for early VocaDig phases."""

from backend.database.database import create_database, create_session_factory


def create_application(database_url: str = "sqlite:///data/vocadig.db") -> None:
    """Initialize the local database used by the backend."""
    session_factory = create_session_factory(database_url)
    create_database(session_factory.kw["bind"])


if __name__ == "__main__":
    create_application()
    print("VocaDig backend initialized.")