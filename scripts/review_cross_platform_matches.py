import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.database import create_database, create_session_factory
from backend.database.models import PlatformVideo
from backend.database.repository import LibraryRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="List and review cross-platform video match proposals.")
    parser.add_argument("--database-url", default="sqlite:///data/vocadig.db")
    parser.add_argument("--suggestion-id", type=int)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--confirm", action="store_true")
    choice.add_argument("--reject", action="store_true")
    arguments = parser.parse_args()
    if (arguments.confirm or arguments.reject) and arguments.suggestion_id is None:
        parser.error("--suggestion-id is required with --confirm or --reject")
    sessions = create_session_factory(arguments.database_url)
    create_database(sessions.kw["bind"])
    with sessions() as session:
        repository = LibraryRepository(session)
        if arguments.suggestion_id is not None and (arguments.confirm or arguments.reject):
            result = repository.review_match_suggestion(arguments.suggestion_id, arguments.confirm)
            print(f"Suggestion {result.id}: {result.status}")
            return
        pending = repository.list_match_suggestions()
        if not pending:
            print("No pending match suggestions.")
            return
        for suggestion in pending:
            left = session.get(PlatformVideo, suggestion.left_video_id)
            right = session.get(PlatformVideo, suggestion.right_video_id)
            assert left is not None and right is not None
            print(f"#{suggestion.id}  confidence={suggestion.confidence:.0%}  "
                  f"{left.platform}:{left.video_id} <-> {right.platform}:{right.video_id}")


if __name__ == "__main__":
    main()
