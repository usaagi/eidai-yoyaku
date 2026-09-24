"""永大産業 新宿ショールームの予約空きを監視し、新しく空いた枠を通知する。"""

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from notify import send_line

BASE_URL = "https://www4.revn.jp/eidai-sangyo-shinjuku/reserve/calendar"
LABEL_ID = "5"  # 新宿ショールーム予約
JST = timezone(timedelta(hours=9))
DEFAULT_DAYS = 14
STATE_PATH = Path(os.environ.get("STATE_PATH", "state.json"))

POPUP_DATA_RE = re.compile(r'class="js_popup_data" value="([^"]*)"')
WEEKDAYS = "月火水木金土日"


@dataclass(frozen=True, order=True)
class Slot:
    date: str
    time: str
    event_id: str

    @property
    def key(self) -> str:
        return f"{self.date} {self.time} {self.event_id}"

    def label(self) -> str:
        d = date.fromisoformat(self.date)
        return f"{d.month}/{d.day}({WEEKDAYS[d.weekday()]}) {self.time}開始"


def fetch_calendar(start: date) -> str:
    url = f"{BASE_URL}?label_id={LABEL_ID}&date={start.isoformat()}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (eidai-yoyaku-watcher)"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def parse_vacant_slots(page: str) -> set[Slot]:
    slots = set()
    for raw in POPUP_DATA_RE.findall(page):
        if not raw:
            continue  # ポップアップのテンプレート用の空要素
        data = json.loads(html.unescape(raw))
        if data.get("can_reserve") and data.get("is_vacant"):
            slots.add(Slot(date=data["date"], time=data["time"], event_id=str(data["id"])))
    return slots


def collect_vacant_slots(today: date, days: int) -> set[Slot]:
    end = today + timedelta(days=days - 1)
    slots: set[Slot] = set()
    # 1リクエストで指定日から7日分が返る
    for offset in range(0, days, 7):
        slots |= parse_vacant_slots(fetch_calendar(today + timedelta(days=offset)))
    return {s for s in slots if today.isoformat() <= s.date <= end.isoformat()}


def load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    return set(json.loads(STATE_PATH.read_text(encoding="utf-8")).get("vacant", []))


def save_state(slots: set[Slot]) -> None:
    STATE_PATH.write_text(
        json.dumps({"vacant": sorted(s.key for s in slots)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_message(new_slots: list[Slot]) -> str:
    lines = ["【永大産業 新宿ショールーム】予約に空きが出ました"]
    lines += [f"・{s.label()}" for s in new_slots]
    lines.append(f"{BASE_URL}?label_id={LABEL_ID}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=int(os.environ.get("WATCH_DAYS", DEFAULT_DAYS)))
    parser.add_argument("--dry-run", action="store_true", help="通知せずメッセージを表示する")
    args = parser.parse_args()

    today = datetime.now(JST).date()
    current = collect_vacant_slots(today, args.days)
    previous = load_state()
    new_slots = sorted(s for s in current if s.key not in previous)

    print(f"{today} から{args.days}日間: 空き {len(current)} 枠 / 新規 {len(new_slots)} 枠")
    if new_slots:
        message = build_message(new_slots)
        if args.dry_run:
            print(message)
        else:
            send_line(message)
    # 通知に失敗した場合は状態を更新せず、次回再送する
    if not args.dry_run:
        save_state(current)
    return 0


if __name__ == "__main__":
    sys.exit(main())
