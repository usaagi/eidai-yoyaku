"""LINE 通知（独自の GAS Web API 経由）。"""

import json
import os
import urllib.parse
import urllib.request


def send_line(message: str) -> None:
    # URL を知っていれば誰でも送信できるため、コードに書かず環境変数から読む
    url = os.environ["NOTIFY_URL"]
    body = urllib.parse.urlencode({"to": "line", "message": message}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # GAS は 302 で結果URLへリダイレクトする。urllib は GET で追従する
    with urllib.request.urlopen(req, timeout=30) as res:
        result = json.loads(res.read().decode("utf-8"))
    if result.get("status") != 200:
        raise RuntimeError(f"LINE 通知に失敗しました: {result.get('message')}")
