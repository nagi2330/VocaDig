import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.crawler.niconico import (
    NiconicoCrawler,
    NiconicoCrawlerConfig,
)
from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository
from backend.settings import DEFAULT_CONFIG_PATH, NiconicoSettings, load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Niconico JSON search results into VocaDig."
    )
    parser.add_argument("endpoint", nargs="?", default=argparse.SUPPRESS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--database-url", default=argparse.SUPPRESS)
    parser.add_argument("--query", default=argparse.SUPPRESS)
    parser.add_argument("--max-pages", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--proxy", default=argparse.SUPPRESS)
    parser.add_argument("--user-agent", default=argparse.SUPPRESS)
    return parser


def crawler_config_from(
    settings: NiconicoSettings, arguments: argparse.Namespace
) -> NiconicoCrawlerConfig:
    overrides = {
        field: getattr(arguments, argument_name)
        for field, argument_name in (
            ("endpoint", "endpoint"),
            ("query", "query"),
            ("max_pages", "max_pages"),
            ("proxy_url", "proxy"),
            ("user_agent", "user_agent"),
        )
        if hasattr(arguments, argument_name)
    }
    resolved = replace(settings, **overrides)
    return NiconicoCrawlerConfig(**vars(resolved))


def main() -> None:
    parser = build_parser()
    arguments = parser.parse_args()
    settings = load_settings(arguments.config)
    database_url = getattr(arguments, "database_url", settings.database.url)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    sessions = create_session_factory(database_url)
    create_database(sessions.kw["bind"])
    with sessions() as session:
        crawler = NiconicoCrawler(
            crawler_config_from(settings.niconico, arguments)
        )
        print(f"Imported {crawler.crawl(LibraryRepository(session))} new songs.")


if __name__ == "__main__":
    main()
