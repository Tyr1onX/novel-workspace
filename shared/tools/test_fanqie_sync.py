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

    def test_safe_reschedule_plan_matches_partial_rail_recovery(self):
        current_days = {}
        for number in (114, 115):
            current_days[number] = "2026-09-08"
        current_days[116] = "2026-09-09"
        for number in range(117, 120):
            current_days[number] = "2026-09-10"
        for number in range(120, 123):
            current_days[number] = "2026-09-11"
        for number in range(123, 126):
            current_days[number] = "2026-09-12"
        for number in range(126, 129):
            current_days[number] = "2026-09-13"
        current_days[129] = "2026-09-14"
        for number in range(130, 134):
            current_days[number] = "2026-09-10"
        for number in range(134, 139):
            current_days[number] = "2026-09-11"
        for number in range(139, 144):
            current_days[number] = "2026-09-12"
        for number in range(144, 149):
            current_days[number] = "2026-09-13"
        for number in range(149, 154):
            current_days[number] = "2026-09-14"
        for number in range(154, 157):
            current_days[number] = "2026-09-15"
        for number in (157, 158):
            current_days[number] = "2026-09-20"

        rows = [
            {
                "title": f"第{number}章",
                "date": current_days[number],
                "time": "00:00",
            }
            for number in range(114, 159)
        ]
        schedule_map = {
            f"第{number}章": (
                f"2026-09-{7 + (number - 114) // 5:02d}",
                "00:00",
            )
            for number in range(114, 159)
        }

        filtered, skipped, day_order = fanqie_runtime_bridge.build_safe_reschedule_plan(
            rows, schedule_map
        )
        self.assertEqual(len(filtered), 18)
        self.assertEqual(len(skipped), 27)
        self.assertEqual(
            day_order,
            [
                "2026-09-07",
                "2026-09-15",
                "2026-09-08",
                "2026-09-09",
                "2026-09-10",
            ],
        )

    def test_safe_reschedule_plan_rejects_dependency_cycle(self):
        rows = [
            {"title": "A", "date": "2026-09-07", "time": "00:00"},
            {"title": "B", "date": "2026-09-08", "time": "00:00"},
        ]
        schedule_map = {
            "A": ("2026-09-08", "00:00"),
            "B": ("2026-09-07", "00:00"),
        }
        with self.assertRaisesRegex(fanqie_runtime_bridge.BridgeError, "dependency cycle"):
            fanqie_runtime_bridge.build_safe_reschedule_plan(rows, schedule_map)

    def test_safe_reschedule_plan_rejects_unmanaged_target_day_occupant(self):
        rows = [
            {"title": "managed", "date": "2026-09-08", "time": "00:00"},
            {"title": "foreign", "date": "2026-09-07", "time": "00:00"},
        ]
        schedule_map = {"managed": ("2026-09-07", "00:00")}
        with self.assertRaisesRegex(fanqie_runtime_bridge.BridgeError, "unmanaged chapter"):
            fanqie_runtime_bridge.build_safe_reschedule_plan(rows, schedule_map)

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

    def test_create_execution_numbers_filters_audited_existing_subset(self):
        op = {
            "id": "create-missing",
            "action": "create",
            "audit": {"already_present_chapters": "86-88"},
        }
        self.assertEqual(
            fanqie_sync.create_execution_numbers(op, [86, 87, 88, 89, 90]),
            [89, 90],
        )

    def test_create_execution_numbers_rejects_audited_chapters_outside_selector(self):
        op = {
            "id": "bad-existing",
            "action": "create",
            "audit": {"already_present_chapters": "85"},
        }
        with self.assertRaisesRegex(fanqie_sync.SyncError, "outside create selector"):
            fanqie_sync.create_execution_numbers(op, [86, 87, 88, 89, 90])

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
