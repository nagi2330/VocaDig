import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.crawler.bilibili import BilibiliFavoritesConfig, BilibiliFavoritesCrawler
from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync a Bilibili favorite folder into VocaDig.")
    parser.add_argument("--media-id", type=int, required=True, help="Bilibili favourite folder media_id")
    parser.add_argument("--user-id", required=True, help="VocaDig local user ID")
    parser.add_argument("--database-url", default="sqlite:///data/vocadig.db")
    parser.add_argument("--cookie-env", default="BILIBILI_COOKIE", help="Environment variable containing the Bilibili Cookie header")
    parser.add_argument("--max-pages", type=int, default=100)
    arguments = parser.parse_args()
    cookie = os.environ.get(arguments.cookie_env)
    if not cookie:
        parser.error(f"Set {arguments.cookie_env} to your Bilibili Cookie header before syncing.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    sessions = create_session_factory(arguments.database_url)
    create_database(sessions.kw["bind"])
    with sessions() as session:
        crawler = BilibiliFavoritesCrawler(BilibiliFavoritesConfig(media_id=arguments.media_id, cookie=cookie, max_pages=arguments.max_pages))
        imported = crawler.crawl(LibraryRepository(session), arguments.user_id)
        print(f"Imported {imported} new Bilibili videos.")


if __name__ == "__main__":
    main()
