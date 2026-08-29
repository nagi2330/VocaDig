import pytest

from backend.database.database import create_database, create_session_factory


@pytest.fixture
def session():
    sessions = create_session_factory("sqlite:///:memory:")
    create_database(sessions.kw["bind"])
    with sessions() as database_session:
        yield database_session