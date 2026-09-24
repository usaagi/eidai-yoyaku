from datetime import date
from pathlib import Path

from check import Slot, build_message, parse_vacant_slots, watch_range

FIXTURE = Path(__file__).parent / "fixtures" / "calendar.html"


def test_parse_vacant_slots_only_returns_reservable():
    slots = parse_vacant_slots(FIXTURE.read_text(encoding="utf-8"))
    assert slots == {
        Slot("2026-10-15", "10:00", "5761"),
        Slot("2026-10-15", "15:00", "5763"),
        Slot("2026-10-16", "15:00", "5763"),
    }


def test_watch_range_is_capped_by_until():
    assert watch_range(date(2026, 9, 24), 21, date(2026, 10, 14)) == (date(2026, 9, 24), date(2026, 10, 14))
    assert watch_range(date(2026, 10, 1), 21, date(2026, 10, 14)) == (date(2026, 10, 1), date(2026, 10, 14))
    assert watch_range(date(2026, 9, 1), 21, date(2026, 10, 14)) == (date(2026, 9, 1), date(2026, 9, 21))
    assert watch_range(date(2026, 9, 24), 21, None) == (date(2026, 9, 24), date(2026, 10, 14))


def test_build_message():
    msg = build_message([Slot("2026-10-15", "10:00", "5761")])
    assert "・10/15(木) 10:00開始" in msg
