from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from detection_service.minimal_baseline import (
    extract_baseline_features,
    generate_procedural_seed_images,
    train_and_evaluate_minimal_baseline,
)


class MinimalBaselineTest(unittest.TestCase):
    def test_feature_extraction_shape_is_stable(self):
        image = generate_procedural_seed_images(count=1)[0]
        features = extract_baseline_features(image)
        self.assertEqual(features.shape, (12,))

    def test_minimal_baseline_can_train_and_evaluate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            result = train_and_evaluate_minimal_baseline(
                seed_dir=temp_root / "missing_seed_dir",
                model_output_path=temp_root / "artifacts" / "model.pkl",
                dataset_output_dir=temp_root / "artifacts" / "dataset",
                eval_output_path=temp_root / "artifacts" / "eval.json",
                variants_per_seed=2,
                test_size=0.25,
                random_state=7,
            )
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["metrics"]["train_size"], 0)
        self.assertGreater(result["metrics"]["test_size"], 0)
        self.assertTrue(result["predictions"])


if __name__ == "__main__":
    unittest.main()
