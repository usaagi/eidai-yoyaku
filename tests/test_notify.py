import io
import json
import urllib.parse

import pytest

import notify


def _fake_urlopen(response: dict, captured: list):
    def fake(req, timeout):
        captured.append(req)
        return io.BytesIO(json.dumps(response).encode())

    return fake


def test_send_line_posts_form(monkeypatch):
    captured = []
    monkeypatch.setenv("NOTIFY_URL", "https://example.com/exec")
    monkeypatch.setattr(notify.urllib.request, "urlopen", _fake_urlopen({"status": 200}, captured))
    notify.send_line("テスト")
    req = captured[0]
    assert req.get_method() == "POST"
    assert urllib.parse.parse_qs(req.data.decode()) == {"to": ["line"], "message": ["テスト"]}


def test_send_line_raises_on_error_status(monkeypatch):
    monkeypatch.setenv("NOTIFY_URL", "https://example.com/exec")
    monkeypatch.setattr(notify.urllib.request, "urlopen", _fake_urlopen({"status": 500, "message": "x"}, []))
    with pytest.raises(RuntimeError):
        notify.send_line("テスト")
