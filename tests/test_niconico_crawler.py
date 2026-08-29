from backend.crawler.niconico import NiconicoCrawler, NiconicoCrawlerConfig
from backend.database.repository import LibraryRepository


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttp:
    def __init__(self):
        self.calls = 0
        self.headers = {}
        self.proxies = {}
        self.params = None

    def get(self, *args, **kwargs):
        self.calls += 1
        self.params = kwargs["params"]
        return FakeResponse(
            {
                "data": [
                    {
                        "contentId": "sm9",
                        "title": "New Vocaloid Song",
                        "tags": ["VOCALOID", "original"],
                        "viewCounter": 100,
                    },
                    {"contentId": "broken"},
                ]
            }
        )


def test_crawler_inserts_new_songs_and_skips_duplicates(session):
    repository = LibraryRepository(session)
    http = FakeHttp()
    crawler = NiconicoCrawler(
        NiconicoCrawlerConfig(endpoint="https://example.invalid", page_size=100), http
    )

    assert crawler.crawl(repository) == 1
    assert crawler.crawl(repository) == 0
    song = repository.get_song("sm9")
    assert song.tags == "VOCALOID,original"
    assert song.view_count == 100
    assert http.params["_offset"] == 0
    assert http.params["_limit"] == 100
    assert "contentId" in http.params["fields"]
