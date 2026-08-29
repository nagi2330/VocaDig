from backend.crawler.bilibili import BilibiliFavoritesConfig, BilibiliFavoritesCrawler
from backend.database.models import PlatformVideo
from backend.database.repository import LibraryRepository


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"has_more": False, "medias": [{
            "bvid": "BV1test", "title": "Miku Original Song", "duration": "03:20",
            "pubtime": 1_700_000_000, "upper": {"name": "Composer"},
            "cnt_info": {"play": 10, "collect": 2, "reply": 1},
        }]}}


class FakeHttp:
    def __init__(self):
        self.headers = {}

    def get(self, *args, **kwargs):
        return FakeResponse()


def test_bilibili_favorite_sync_auto_links_an_exact_niconico_match(session):
    repository = LibraryRepository(session)
    repository.upsert_platform_song("niconico", "sm9", {
        "song_id": "sm9", "title": "Miku Original Song", "producer": "Composer", "duration": 200,
    })
    crawler = BilibiliFavoritesCrawler(
        BilibiliFavoritesConfig(media_id=123, cookie="SESSDATA=secret"), FakeHttp()
    )

    assert crawler.crawl(repository, "user-1") == 1
    suggestions = repository.list_match_suggestions("confirmed")
    assert len(suggestions) == 1
    assert suggestions[0].auto_matched
    videos = list(session.query(PlatformVideo).order_by(PlatformVideo.platform))
    assert {video.platform for video in videos} == {"bilibili", "niconico"}
    assert videos[0].canonical_song_id == videos[1].canonical_song_id
    assert [favorite.song_id for favorite in repository.list_favorites("user-1")] == ["bilibili:BV1test"]
    assert [song.song_id for song in repository.get_platform_counterparts("bilibili:BV1test", "niconico")] == ["sm9"]


def test_similar_match_waits_for_user_confirmation(session):
    repository = LibraryRepository(session)
    repository.upsert_platform_song("niconico", "sm10", {
        "song_id": "sm10", "title": "Miku Original Song", "producer": "Composer", "duration": 200,
    })
    repository.upsert_platform_song("bilibili", "BV2test", {
        "song_id": "bilibili:BV2test", "title": "Miku Original Songs", "producer": "", "duration": 200,
    })

    suggestions = repository.suggest_niconico_matches("bilibili:BV2test")
    assert len(suggestions) == 1
    assert suggestions[0].status == "pending"
    reviewed = repository.review_match_suggestion(suggestions[0].id, confirmed=True)
    assert reviewed.status == "confirmed"
