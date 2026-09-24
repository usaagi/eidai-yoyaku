import io
import json
import urllib.parse

import pytest

import notify


def _fake_urlopen(responses: dict, captured: list):
    def fake(req, timeout):
        captured.append(req)
        to = urllib.parse.parse_qs(req.data.decode())["to"][0]
        return io.BytesIO(json.dumps(responses[to]).encode())

    return fake


OK = {"line": {"status": 200}, "discord": {"status": 200}, "slack": {"status": 200}}


def test_send_notification_posts_to_all_destinations(monkeypatch):
    captured = []
    monkeypatch.setenv("NOTIFY_URL", "https://example.com/exec")
    monkeypatch.setattr(notify.urllib.request, "urlopen", _fake_urlopen(OK, captured))
    notify.send_notification("テスト")
    assert all(req.get_method() == "POST" for req in captured)
    assert [urllib.parse.parse_qs(req.data.decode()) for req in captured] == [
        {"to": [to], "message": ["テスト"]} for to in ("line", "discord", "slack")
    ]


def test_send_notification_continues_after_failure_and_raises(monkeypatch):
    captured = []
    responses = {**OK, "line": {"status": 500, "message": "x"}}
    monkeypatch.setenv("NOTIFY_URL", "https://example.com/exec")
    monkeypatch.setattr(notify.urllib.request, "urlopen", _fake_urlopen(responses, captured))
    with pytest.raises(RuntimeError, match="line"):
        notify.send_notification("テスト")
    assert len(captured) == 3
