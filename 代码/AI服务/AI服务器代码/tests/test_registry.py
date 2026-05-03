from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from detection_service import DetectionModelRegistry, ValidationError


class DetectionModelRegistryTest(unittest.TestCase):
    def test_default_registry_exposes_profiles(self):
        registry = DetectionModelRegistry.load()
        self.assertEqual(registry.default_image_profile, "default")
        self.assertIn("default", registry.image_profile_names())
        self.assertIn("fast", registry.image_profile_names())
        self.assertIn("minimal_trainable", registry.image_profile_names())
        self.assertIn("splicing", registry.describe_image_profiles()["default"]["enabled_methods"])

    def test_build_image_detector_uses_profile_methods(self):
        registry = DetectionModelRegistry.load()
        default_detector = registry.build_image_detector("default")
        fast_detector = registry.build_image_detector("fast")
        minimal_detector = registry.build_image_detector("minimal_trainable")

        self.assertIn("llm", default_detector.method_names)
        self.assertNotIn("llm", fast_detector.method_names)
        self.assertEqual(fast_detector.method_names, ["ela", "exif", "cmd", "splicing"])
        self.assertEqual(minimal_detector.method_names, ["exif", "splicing"])

    def test_unknown_profile_raises_validation_error(self):
        registry = DetectionModelRegistry.load()
        with self.assertRaises(ValidationError):
            registry.resolve_image_profile("missing")


if __name__ == "__main__":
    unittest.main()
