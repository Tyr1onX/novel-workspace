import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("fanqie_probe.py")
spec = importlib.util.spec_from_file_location("fanqie_probe", MODULE_PATH)
fanqie_probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["fanqie_probe"] = fanqie_probe
spec.loader.exec_module(fanqie_probe)


class FanqieProbeTests(unittest.TestCase):
    def test_resolve_runtime_from_runner_sibling(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime = root / "publisher"
            runtime.mkdir()
            (runtime / "fanqie_upload.py").write_text("# test\n", encoding="utf-8")
            runner_temp = root / "runner" / "_work" / "_temp"
            runner_temp.mkdir(parents=True)

            env = {
                "RUNNER_TEMP": str(runner_temp),
                "FANQIE_RUNTIME_DIR": "",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                resolved = fanqie_probe.resolve_runtime()

            self.assertEqual(resolved, runtime.resolve())

    def test_explicit_invalid_runtime_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(fanqie_probe.ProbeError):
                fanqie_probe.resolve_runtime(str(Path(td) / "missing"))

    def test_output_contains_exact_book_id(self):
        output = "找到 1 部作品:\n  1. 测试书\n     ID: 7670480372831882302\n"
        self.assertTrue(
            fanqie_probe.output_contains_book_id(output, "7670480372831882302")
        )
        self.assertFalse(
            fanqie_probe.output_contains_book_id(output, "7670480372831882303")
        )


if __name__ == "__main__":
    unittest.main()
