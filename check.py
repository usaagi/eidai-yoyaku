"""永大産業 新宿ショールームの予約空きを監視し、空いている枠があれば毎回通知する。"""

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from notify import send_line

BASE_URL = "https://www4.revn.jp/eidai-sangyo-shinjuku/reserve/calendar"
LABEL_ID = "5"  # 新宿ショールーム予約
JST = timezone(timedelta(hours=9))
DEFAULT_DAYS = 21

POPUP_DATA_RE = re.compile(r'class="js_popup_data" value="([^"]*)"')
WEEKDAYS = "月火水木金土日"


@dataclass(frozen=True, order=True)
class Slot:
    date: str
    time: str
    event_id: str

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


def watch_range(today: date, days: int, until: date | None) -> tuple[date, date]:
    end = today + timedelta(days=days - 1)
    if until is not None:
        end = min(end, until)
    return today, end


def collect_vacant_slots(start: date, end: date) -> set[Slot]:
    slots: set[Slot] = set()
    # 1リクエストで指定日から7日分が返る
    for offset in range(0, (end - start).days + 1, 7):
        slots |= parse_vacant_slots(fetch_calendar(start + timedelta(days=offset)))
    return {s for s in slots if start.isoformat() <= s.date <= end.isoformat()}


def build_message(slots: list[Slot]) -> str:
    lines = ["【永大産業 新宿ショールーム】予約に空きがあります"]
    lines += [f"・{s.label()}" for s in slots]
    lines.append(f"{BASE_URL}?label_id={LABEL_ID}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=int(os.environ.get("WATCH_DAYS", DEFAULT_DAYS)))
    parser.add_argument(
        "--until",
        type=date.fromisoformat,
        default=os.environ.get("WATCH_UNTIL") or None,
        help="監視する最終日 (YYYY-MM-DD)",
    )
    parser.add_argument("--dry-run", action="store_true", help="通知せずメッセージを表示する")
    args = parser.parse_args()

    start, end = watch_range(datetime.now(JST).date(), args.days, args.until)
    if end < start:
        print(f"監視期間終了（最終日 {end}）")
        return 0

    slots = sorted(collect_vacant_slots(start, end))
    print(f"{start} 〜 {end}: 空き {len(slots)} 枠")
    if slots:
        message = build_message(slots)
        if args.dry_run:
            print(message)
        else:
            send_line(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
