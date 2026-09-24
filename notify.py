"""LINE / Discord / Slack 通知（独自の GAS Web API 経由）。"""

import json
import os
import urllib.parse
import urllib.request

DESTINATIONS = ("line", "discord", "slack")


def _send(url: str, to: str, message: str) -> None:
    body = urllib.parse.urlencode({"to": to, "message": message}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # GAS は 302 で結果URLへリダイレクトする。urllib は GET で追従する
    with urllib.request.urlopen(req, timeout=30) as res:
        result = json.loads(res.read().decode("utf-8"))
    # 送信先の HTTP ステータスがそのまま返る。Discord Webhook は成功時 204
    status = result.get("status")
    if not (isinstance(status, int) and 200 <= status < 300):
        raise RuntimeError(f"{to} 通知に失敗しました: {result}")


def send_notification(message: str) -> None:
    # URL を知っていれば誰でも送信できるため、コードに書かず環境変数から読む
    url = os.environ["NOTIFY_URL"]
    # 1か所が失敗しても残りには送り、最後にまとめて失敗を伝える
    errors = []
    for to in DESTINATIONS:
        try:
            _send(url, to, message)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{to}: {e}")
    if errors:
        raise RuntimeError("通知に失敗しました: " + " / ".join(errors))
