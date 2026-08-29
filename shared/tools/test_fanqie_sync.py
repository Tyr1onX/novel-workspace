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
