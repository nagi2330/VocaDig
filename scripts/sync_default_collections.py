import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository
from backend.sync.favorite_collections import FavoriteCollectionSyncService


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize due default favourite collections.")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--database-url", default="sqlite:///data/vocadig.db")
    parser.add_argument("--force", action="store_true", help="Sync even if the configured interval has not elapsed")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    sessions = create_session_factory(arguments.database_url)
    create_database(sessions.kw["bind"])
    with sessions() as session:
        reports = FavoriteCollectionSyncService(LibraryRepository(session)).sync_due(
            arguments.user_id, force=arguments.force
        )
        for report in reports:
            difference = report.difference
            print(f"#{report.collection_id} {report.platform}: +{len(difference.added_song_ids)} "
                  f"-{len(difference.removed_song_ids)} ={difference.unchanged_count}")
        if not reports:
            print("No collections are due for synchronization.")


if __name__ == "__main__":
    main()
