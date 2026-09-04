import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("fanqie_sync.py")
spec = importlib.util.spec_from_file_location("fanqie_sync", MODULE_PATH)
fanqie_sync = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["fanqie_sync"] = fanqie_sync
spec.loader.exec_module(fanqie_sync)

BRIDGE_PATH = Path(__file__).with_name("fanqie_runtime_bridge.py")
bridge_spec = importlib.util.spec_from_file_location("fanqie_runtime_bridge", BRIDGE_PATH)
fanqie_runtime_bridge = importlib.util.module_from_spec(bridge_spec)
assert bridge_spec.loader is not None
bridge_spec.loader.exec_module(fanqie_runtime_bridge)

COMPAT_PATH = Path(__file__).with_name("fanqie_compat.py")
compat_spec = importlib.util.spec_from_file_location("fanqie_compat", COMPAT_PATH)
fanqie_compat = importlib.util.module_from_spec(compat_spec)
assert compat_spec.loader is not None
compat_spec.loader.exec_module(fanqie_compat)


def strict_policy() -> dict:
    return {
        "version": 1,
        "book_id": "book",
        "chapter_length": {"hard_minimum_chars": 2001},
        "schedule": {
            "mode": "fixed_start",
            "chapters_per_day": 3,
            "group_size": 3,
            "slots": ["00:00"],
            "require_complete_groups": True,
            "daily_word_floor": {
                "enabled": True,
                "minimum_chars_exclusive": 6000,
                "normal_chapters": 3,
            },
        },
    }


def make_chapters(root: Path, lengths: list[int]) -> dict[int, object]:
    chapters = {}
    for number, length in enumerate(lengths, 1):
        path = root / f"chapter-{number}.md"
        path.write_text(
            f"# 第{number}章 标题{number}\n\n" + ("字" * length) + "\n",
            encoding="utf-8",
        )
        chapters[number] = fanqie_sync.parse_chapter(path)
    return chapters


class FanqieSyncTests(unittest.TestCase):
    def test_parse_chapter_separates_heading_and_body(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "chapter-107.md"
            p.write_text("# 第107章 测试标题\n\n第一段。\n\n第二段。\n", encoding="utf-8")
            ch = fanqie_sync.parse_chapter(p)
            self.assertEqual(ch.number, 107)
            self.assertEqual(ch.title, "测试标题")
            self.assertEqual(ch.body, "第一段。\n\n第二段。\n")
            self.assertNotIn("第107章", ch.body)

    def test_parse_chapter_rejects_number_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "chapter-108.md"
            p.write_text("# 第109章 错号\n\n正文。\n", encoding="utf-8")
            with self.assertRaises(fanqie_sync.SyncError):
                fanqie_sync.parse_chapter(p)

    def test_compat_parser_accepts_chinese_numeral_heading(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "chapter-040.md"
            p.write_text("# 第四十章 七公里，找一条蓝绳\n\n正文。\n", encoding="utf-8")
            ch = fanqie_compat.parse_chapter_compat(p)
            self.assertEqual(ch.number, 40)
            self.assertEqual(ch.title, "七公里，找一条蓝绳")

    def test_exact_group_schedule_keeps_all_three_at_midnight(self):
        schedule = fanqie_runtime_bridge.exact_group_schedule(
            8, "2026-09-08", "00:00", 3
        )
        self.assertEqual(
            schedule,
            [
                ("2026-09-08", "00:00"),
                ("2026-09-08", "00:00"),
                ("2026-09-08", "00:00"),
                ("2026-09-09", "00:00"),
                ("2026-09-09", "00:00"),
                ("2026-09-09", "00:00"),
                ("2026-09-10", "00:00"),
                ("2026-09-10", "00:00"),
            ],
        )

    def test_chapter_range_round_trip(self):
        nums = fanqie_sync.parse_chapter_spec("1,3,5-8,10")
        self.assertEqual(nums, [1, 3, 5, 6, 7, 8, 10])
        self.assertEqual(fanqie_sync.compact_spec(nums), "1,3,5-8,10")

    def test_authorized_operation_requires_passed_audit(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "chapter-1.md"
            p.write_text("# 第1章 标题\n\n正文。\n", encoding="utf-8")
            chapters = {1: fanqie_sync.parse_chapter(p)}
            op = {
                "id": "unsafe",
                "action": "update",
                "chapters": "1",
                "authorized": True,
                "audit": {"status": "pending"},
            }
            with self.assertRaises(fanqie_sync.SyncError):
                fanqie_sync.validate_operation(op, chapters)

    def test_strict_create_rejects_auto_continue(self):
        with tempfile.TemporaryDirectory() as td:
            chapters = make_chapters(Path(td), [2001, 2001, 2001])
            op = {
                "id": "bad-auto",
                "action": "create",
                "chapters": "1-3",
                "schedule_mode": "auto_continue",
                "authorized": True,
                "audit": {"status": "passed"},
            }
            with self.assertRaisesRegex(fanqie_sync.SyncError, "require fixed_start"):
                fanqie_sync.validate_release_operation(op, chapters, strict_policy())

    def test_strict_create_rejects_partial_day(self):
        with tempfile.TemporaryDirectory() as td:
            chapters = make_chapters(Path(td), [2100, 2100, 2100, 2100])
            op = {
                "id": "partial",
                "action": "create",
                "chapters": "1-4",
                "schedule_mode": "fixed_start",
                "start_date": "2026-09-05",
                "authorized": True,
                "audit": {"status": "passed"},
            }
            with self.assertRaisesRegex(fanqie_sync.SyncError, "partial release day"):
                fanqie_sync.validate_release_operation(op, chapters, strict_policy())

    def test_strict_create_requires_daily_total_strictly_over_floor(self):
        with tempfile.TemporaryDirectory() as td:
            policy = strict_policy()
            policy["chapter_length"]["hard_minimum_chars"] = 2000
            chapters = make_chapters(Path(td), [2000, 2000, 2000])
            op = {
                "id": "exactly-six-thousand",
                "action": "create",
                "chapters": "1-3",
                "schedule_mode": "fixed_start",
                "start_date": "2026-09-05",
                "authorized": True,
                "audit": {"status": "passed"},
            }
            with self.assertRaisesRegex(fanqie_sync.SyncError, "must be > 6000"):
                fanqie_sync.validate_release_operation(op, chapters, policy)

    def test_strict_create_accepts_complete_group_over_floor(self):
        with tempfile.TemporaryDirectory() as td:
            chapters = make_chapters(Path(td), [2001, 2001, 2001])
            op = {
                "id": "good",
                "action": "create",
                "chapters": "1-3",
                "schedule_mode": "fixed_start",
                "start_date": "2026-09-05",
                "authorized": True,
                "audit": {"status": "passed"},
            }
            self.assertEqual(
                fanqie_sync.validate_release_operation(op, chapters, strict_policy()),
                [1, 2, 3],
            )

    def test_strict_reschedule_requires_reconciled_pending_set(self):
        with tempfile.TemporaryDirectory() as td:
            chapters = make_chapters(Path(td), [2001, 2001, 2001])
            op = {
                "id": "reschedule",
                "action": "reschedule_all",
                "start_date": "2026-09-05",
                "authorized": True,
                "audit": {"status": "passed"},
            }
            with self.assertRaisesRegex(fanqie_sync.SyncError, "expected_pending_chapters"):
                fanqie_sync.validate_release_operation(op, chapters, strict_policy())

    def test_empty_queue_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chapters" / "volume-01").mkdir(parents=True)
            (root / "platform-sync").mkdir()
            (root / "chapters" / "volume-01" / "chapter-001.md").write_text(
                "# 第1章 标题\n\n正文。\n", encoding="utf-8"
            )
            config = {
                "version": 1,
                "book_id": "book",
                "chapter_glob": "chapters/volume-*/chapter-*.md",
                "sync_enabled": False,
            }
            policy = {
                "version": 1,
                "book_id": "book",
                "schedule": {
                    "mode": "auto_continue",
                    "chapters_per_day": 2,
                    "slots": ["10:00", "20:00"],
                },
            }
            queue = {"version": 1, "book_id": "book", "operations": []}
            state = {"version": 1, "book_id": "book", "chapters": {}}
            for name, data in {
                "config.json": config,
                "policy.json": policy,
                "queue.json": queue,
                "sync-state.json": state,
            }.items():
                (root / "platform-sync" / name).write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8"
                )
            plan = fanqie_sync.build_plan(root)
            self.assertEqual(plan["pending_count"], 0)
            self.assertFalse(plan["enabled"])


if __name__ == "__main__":
    unittest.main()
