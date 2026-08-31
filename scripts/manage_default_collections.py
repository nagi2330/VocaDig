import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository
from backend.settings import DEFAULT_CONFIG_PATH, load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage a user's monitored favourite collections.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--database-url", default=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Add or update a default collection")
    add.add_argument("--user-id", required=True)
    add.add_argument("--platform", choices=("niconico", "bilibili"), required=True)
    add.add_argument("--remote-id", required=True, help="Niconico mylist ID or Bilibili media_id")
    add.add_argument("--name")
    add.add_argument("--credential-env", help="Environment variable containing the platform Cookie")
    add.add_argument("--interval-minutes", type=int, default=argparse.SUPPRESS)
    listing = commands.add_parser("list", help="List enabled default collections")
    listing.add_argument("--user-id", required=True)
    remove = commands.add_parser("remove", help="Remove a collection and songs not in another monitored collection")
    remove.add_argument("--user-id", required=True)
    remove.add_argument("--collection-id", type=int, required=True)
    arguments = parser.parse_args()
    settings = load_settings(arguments.config)
    sessions = create_session_factory(getattr(arguments, "database_url", settings.database.url))
    create_database(sessions.kw["bind"])
    with sessions() as session:
        repository = LibraryRepository(session)
        if arguments.command == "add":
            collection = repository.save_default_collection(
                arguments.user_id, arguments.platform, arguments.remote_id,
                name=arguments.name, credential_env=arguments.credential_env,
                sync_interval_minutes=getattr(
                    arguments, "interval_minutes", settings.collections.sync_interval_minutes
                ),
            )
            print(f"Saved collection #{collection.id}: {collection.platform}:{collection.remote_id}")
            return
        if arguments.command == "remove":
            if not repository.remove_default_collection(arguments.user_id, arguments.collection_id):
                parser.error(f"No collection #{arguments.collection_id} belongs to user {arguments.user_id}")
            print(f"Removed collection #{arguments.collection_id} and songs not found in another monitored collection.")
            return
        for collection in repository.list_default_collections(arguments.user_id):
            print(f"#{collection.id} {collection.platform}:{collection.remote_id} "
                  f"every {collection.sync_interval_minutes}m {collection.name or ''}")


if __name__ == "__main__":
    main()
