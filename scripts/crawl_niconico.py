import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.crawler.niconico import (
    SNAPSHOT_SEARCH_ENDPOINT,
    NiconicoCrawler,
    NiconicoCrawlerConfig,
)
from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Niconico JSON search results into VocaDig."
    )
    parser.add_argument(
        "endpoint",
        nargs="?",
        default=SNAPSHOT_SEARCH_ENDPOINT,
        help="Niconico JSON endpoint (defaults to the official Snapshot Search API)",
    )
    parser.add_argument("--database-url", default="sqlite:///data/vocadig.db")
    parser.add_argument("--query", default="VOCALOID")
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument(
        "--proxy", help="HTTP(S) proxy URL, for example http://127.0.0.1:7890"
    )
    parser.add_argument(
        "--user-agent", default="VocaDig/0.1 (personal music discovery)"
    )
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    sessions = create_session_factory(arguments.database_url)
    create_database(sessions.kw["bind"])
    with sessions() as session:
        crawler = NiconicoCrawler(
            NiconicoCrawlerConfig(
                endpoint=arguments.endpoint,
                query=arguments.query,
                max_pages=arguments.max_pages,
                proxy_url=arguments.proxy,
                user_agent=arguments.user_agent,
            )
        )
        print(f"Imported {crawler.crawl(LibraryRepository(session))} new songs.")


if __name__ == "__main__":
    main()
