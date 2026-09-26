import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_menu.py"
spec = importlib.util.spec_from_file_location("update_menu", MODULE_PATH)
update_menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_menu)

TZ = ZoneInfo("Atlantic/Faroe")


def dt(value):
    return datetime.fromisoformat(value).astimezone(TZ)


def fake_payload(week_start, label="FAKE"):
    return {
        "source": "test",
        "week_start": week_start,
        "updated_at": "2026-08-14T12:00:00Z",
        "days": [{"day": d, "dish": f"{label} {d}"} for d in update_menu.DAYS],
    }


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.current = self.root / "menu.json"
        self.next = self.root / "menu-next.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_friday_boundary(self):
        self.assertEqual(
            update_menu.output_path_for_time(dt("2026-08-14T12:59:59+01:00"), self.current, self.next),
            self.current,
        )
        self.assertEqual(
            update_menu.output_path_for_time(dt("2026-08-14T13:00:00+01:00"), self.current, self.next),
            self.next,
        )

    def test_weekend_goes_to_next(self):
        for value in ("2026-08-15T10:00:00+01:00", "2026-08-16T10:00:00+01:00"):
            self.assertEqual(update_menu.output_path_for_time(dt(value), self.current, self.next), self.next)

    def test_week_labels(self):
        fri_morning = dt("2026-08-14T12:00:00+01:00")
        fri_afternoon = dt("2026-08-14T15:30:00+01:00")
        self.assertEqual(update_menu.target_week_start(fri_morning, self.current, self.current), "2026-08-10")
        self.assertEqual(update_menu.target_week_start(fri_afternoon, self.next, self.current), "2026-08-17")

    def test_friday_afternoon_does_not_change_current(self):
        original = fake_payload("2026-08-10", "CURRENT")
        update_menu.atomic_write_json(self.current, original)

        now = dt("2026-08-14T15:30:00+01:00")
        output = update_menu.run_update(
            now,
            fetcher=lambda ws: fake_payload(ws, "NEXT"),
            current=self.current,
            next_path=self.next,
        )

        self.assertEqual(output, self.next)
        self.assertEqual(json.loads(self.current.read_text()), original)
        next_payload = json.loads(self.next.read_text())
        self.assertEqual(next_payload["week_start"], "2026-08-17")

    def test_valid_monday_promotion(self):
        update_menu.atomic_write_json(self.next, fake_payload("2026-08-17", "NEXT"))
        promoted = update_menu.promote_next_menu(
            dt("2026-08-17T01:17:00+01:00"), self.current, self.next
        )
        self.assertTrue(promoted)
        self.assertTrue(self.current.exists())
        self.assertFalse(self.next.exists())
        self.assertEqual(json.loads(self.current.read_text())["week_start"], "2026-08-17")

    def test_stale_next_is_never_promoted(self):
        update_menu.atomic_write_json(self.next, fake_payload("2026-08-10", "STALE"))
        promoted = update_menu.promote_next_menu(
            dt("2026-08-17T01:17:00+01:00"), self.current, self.next
        )
        self.assertFalse(promoted)
        self.assertFalse(self.current.exists())
        self.assertFalse(self.next.exists())

    def test_monday_update_writes_current_week(self):
        now = dt("2026-08-17T01:17:00+01:00")
        output = update_menu.run_update(
            now,
            fetcher=lambda ws: fake_payload(ws, "MONDAY"),
            current=self.current,
            next_path=self.next,
        )
        self.assertEqual(output, self.current)
        self.assertEqual(json.loads(self.current.read_text())["week_start"], "2026-08-17")


if __name__ == "__main__":
    unittest.main()
