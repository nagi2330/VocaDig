from backend.crawler.cookies import load_cookie_header


def test_cookie_export_sends_only_target_domain_cookies():
    exported = '[{"domain":".bilibili.com","name":"SESSDATA","value":"value-a"},' \
        '{"domain":"space.bilibili.com","name":"sid","value":"value-b"},' \
        '{"domain":".example.com","name":"other","value":"value-c"}]'

    assert load_cookie_header(exported, ".bilibili.com") == "SESSDATA=value-a; sid=value-b"
