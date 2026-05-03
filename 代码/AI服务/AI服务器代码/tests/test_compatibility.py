from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
BACKEND_SCHEMA_PATH = (
    ROOT.parents[2] / "代码" / "后端" / "后端代码" / "core" / "utils" / "ai_result_schema.py"
)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class CompatibilityTest(unittest.TestCase):
    def test_fixture_response_is_accepted_by_backend_schema(self):
        spec = importlib.util.spec_from_file_location("backend_ai_result_schema", BACKEND_SCHEMA_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        response = json.loads((FIXTURES / "compat_image_response.json").read_text(encoding="utf-8"))
        normalized = module.normalize_ai_batch_results(response, expected_count=1)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["image_id"], 123)
        self.assertEqual(normalized[0]["model_version"], "image-detector-fixture-2026-04")
        self.assertTrue(normalized[0]["overall_is_fake"])
        self.assertEqual(normalized[0]["sub_method_results"][0]["method"], "splicing")


if __name__ == "__main__":
    unittest.main()
