import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository
from backend.recommendation import generate_recommendations
from backend.settings import DEFAULT_CONFIG_PATH, load_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate metadata-based baseline recommendations."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--database-url", default=argparse.SUPPRESS)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--limit", type=int, default=20)
    arguments = parser.parse_args()
    settings = load_settings(arguments.config)
    database_url = getattr(arguments, "database_url", settings.database.url)
    sessions = create_session_factory(database_url)
    create_database(sessions.kw["bind"])
    with sessions() as session:
        recommendations = generate_recommendations(
            LibraryRepository(session), arguments.user_id, arguments.limit
        )
    for rank, recommendation in enumerate(recommendations, start=1):
        components = " ".join(
            f"{name}={value:.2f}"
            for name, value in recommendation.score.components.items()
        )
        print(
            f"#{rank} {recommendation.song.song_id} {recommendation.song.title} "
            f"score={recommendation.score.total:.2f} {components}"
        )
    if not recommendations:
        print("No recommendations. Add favorites and import candidate songs first.")


if __name__ == "__main__":
    main()