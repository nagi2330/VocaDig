from pathlib import Path

from backend.settings import NiconicoSettings, load_settings
from scripts.crawl_niconico import build_parser, crawler_config_from


def test_settings_use_code_defaults_when_file_is_missing(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.toml")

    assert settings.database.url == "sqlite:///data/vocadig.db"
    assert settings.niconico.max_pages == 10
    assert settings.bilibili.timeout_seconds == 20.0


def test_settings_override_only_configured_values(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        """[database]
url = "sqlite:///custom.db"

[crawler.niconico]
max_pages = 7

[crawler.bilibili]
timeout_seconds = 5.5
""",
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.database.url == "sqlite:///custom.db"
    assert settings.niconico.max_pages == 7
    assert settings.niconico.page_size == 100
    assert settings.bilibili.timeout_seconds == 5.5
    assert settings.bilibili.max_pages == 100


def test_niconico_cli_value_overrides_toml_setting() -> None:
    arguments = build_parser().parse_args(["--max-pages", "2"])

    config = crawler_config_from(NiconicoSettings(max_pages=7), arguments)

    assert config.max_pages == 2


def test_niconico_omitted_cli_value_preserves_toml_setting() -> None:
    arguments = build_parser().parse_args([])

    config = crawler_config_from(NiconicoSettings(max_pages=7), arguments)

    assert config.max_pages == 7