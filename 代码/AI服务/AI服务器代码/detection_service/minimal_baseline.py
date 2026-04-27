from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .base import DetectionMethod
from .contracts import DetectionContext, DetectionEvidence, ImageInput


FEATURE_NAMES = [
    "gray_mean",
    "gray_std",
    "saturation_mean",
    "saturation_std",
    "value_mean",
    "value_std",
    "laplacian_abs_mean",
    "laplacian_var",
    "edge_density",
    "jpeg_residual_mean",
    "jpeg_residual_std",
    "jpeg_residual_p90",
]

DEFAULT_MODEL_OUTPUT_PATH = Path(__file__).resolve().parent / "artifacts" / "minimal_baseline.pkl"
DEFAULT_DATASET_OUTPUT_DIR = Path(__file__).resolve().parent / "artifacts" / "minimal_dataset"
DEFAULT_EVAL_OUTPUT_PATH = Path(__file__).resolve().parent / "artifacts" / "minimal_baseline_eval.json"
DEFAULT_SEED_DIR = Path(__file__).resolve().parents[3] / "AI训练" / "AI训练代码" / "URN"


@dataclass(slots=True)
class BaselineDatasetItem:
    image_path: Path
    label: int
    source_seed: str


def extract_baseline_features(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    edges = cv2.Canny(gray, 80, 160)
    residual = build_baseline_mask(image_bgr)

    return np.asarray(
        [
            float(gray.mean() / 255.0),
            float(gray.std() / 255.0),
            float(hsv[:, :, 1].mean() / 255.0),
            float(hsv[:, :, 1].std() / 255.0),
            float(hsv[:, :, 2].mean() / 255.0),
            float(hsv[:, :, 2].std() / 255.0),
            float(np.abs(laplacian).mean() / 255.0),
            float(laplacian.var() / (255.0 * 255.0)),
            float(edges.mean() / 255.0),
            float(residual.mean() / 255.0),
            float(residual.std() / 255.0),
            float(np.percentile(residual, 90) / 255.0),
        ],
        dtype=np.float32,
    )


def build_baseline_mask(image_bgr: np.ndarray) -> np.ndarray:
    success, encoded = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not success:
        return np.zeros(image_bgr.shape[:2], dtype=np.float32)
    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if recompressed is None:
        return np.zeros(image_bgr.shape[:2], dtype=np.float32)
    diff = cv2.absdiff(image_bgr, recompressed)
    return cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY).astype(np.float32)


def load_image_bgr(image_path: Path) -> np.ndarray:
    buffer = np.fromfile(str(image_path), dtype=np.uint8)
    if buffer.size == 0:
        raise ValueError(f"failed to read image: {image_path}")
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"failed to read image: {image_path}")
    return image


def save_image_bgr(image_path: Path, image_bgr: np.ndarray) -> None:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = image_path.suffix.lower()
    extension = ".jpg" if suffix in {".jpg", ".jpeg"} else ".png"
    success, encoded = cv2.imencode(extension, image_bgr)
    if not success:
        raise ValueError(f"failed to encode image: {image_path}")
    image_path.write_bytes(encoded.tobytes())


def discover_seed_images(seed_dir: Path) -> list[Path]:
    if seed_dir.exists():
        images = sorted(
            path
            for path in seed_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
            and ".ipynb_checkpoints" not in path.parts
        )
        if images:
            return images
    return []


def generate_procedural_seed_images(count: int = 8, image_size: int = 256) -> list[np.ndarray]:
    images: list[np.ndarray] = []
    for index in range(count):
        canvas = np.full((image_size, image_size, 3), 245, dtype=np.uint8)
        color = (
            int(30 + (index * 29) % 200),
            int(50 + (index * 17) % 180),
            int(70 + (index * 13) % 160),
        )
        cv2.rectangle(canvas, (20, 20), (image_size - 20, image_size - 20), color, thickness=3)
        cv2.circle(canvas, (image_size // 2, image_size // 2), 25 + index * 8, color, thickness=-1)
        cv2.line(canvas, (0, index * 23 % image_size), (image_size, (index * 41 + 50) % image_size), color, 2)
        images.append(canvas)
    return images


def _normalize_canvas(image_bgr: np.ndarray, image_size: int = 256) -> np.ndarray:
    return cv2.resize(image_bgr, (image_size, image_size), interpolation=cv2.INTER_AREA)


def _augment_real(image_bgr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    canvas = _normalize_canvas(image_bgr).copy()
    canvas = cv2.convertScaleAbs(
        canvas,
        alpha=float(rng.uniform(0.92, 1.08)),
        beta=float(rng.uniform(-8.0, 8.0)),
    )
    if rng.random() < 0.5:
        canvas = cv2.GaussianBlur(canvas, (0, 0), sigmaX=float(rng.uniform(0.5, 1.2)))
    if rng.random() < 0.4:
        noise = rng.normal(0.0, 4.0, size=canvas.shape).astype(np.float32)
        canvas = np.clip(canvas.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return canvas


def _augment_fake(image_bgr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    canvas = _augment_real(image_bgr, rng)
    height, width = canvas.shape[:2]
    patch_w = int(rng.integers(max(24, width // 6), max(32, width // 3)))
    patch_h = int(rng.integers(max(24, height // 6), max(32, height // 3)))
    x1 = int(rng.integers(0, max(1, width - patch_w)))
    y1 = int(rng.integers(0, max(1, height - patch_h)))
    patch = canvas[y1 : y1 + patch_h, x1 : x1 + patch_w].copy()

    operation = str(rng.choice(["blur", "contrast", "copy_move", "noise"]))
    if operation == "blur":
        patch = cv2.GaussianBlur(patch, (0, 0), sigmaX=float(rng.uniform(2.0, 4.5)))
        canvas[y1 : y1 + patch_h, x1 : x1 + patch_w] = patch
    elif operation == "contrast":
        patch = cv2.convertScaleAbs(patch, alpha=float(rng.uniform(1.25, 1.8)), beta=float(rng.uniform(10, 35)))
        canvas[y1 : y1 + patch_h, x1 : x1 + patch_w] = patch
    elif operation == "copy_move":
        x2 = int(rng.integers(0, max(1, width - patch_w)))
        y2 = int(rng.integers(0, max(1, height - patch_h)))
        canvas[y2 : y2 + patch_h, x2 : x2 + patch_w] = patch
    else:
        noise = rng.normal(0.0, 22.0, size=patch.shape).astype(np.float32)
        patch = np.clip(patch.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        canvas[y1 : y1 + patch_h, x1 : x1 + patch_w] = patch
    return canvas


def build_synthetic_dataset(
    seed_dir: Path,
    output_dir: Path,
    *,
    variants_per_seed: int = 6,
    random_state: int = 42,
) -> list[BaselineDatasetItem]:
    rng = np.random.default_rng(random_state)
    seed_images = discover_seed_images(seed_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    materialized: list[tuple[str, np.ndarray]] = []
    if seed_images:
        for seed_path in seed_images:
            try:
                materialized.append((seed_path.stem, load_image_bgr(seed_path)))
            except ValueError:
                continue
    if not materialized:
        for index, image in enumerate(generate_procedural_seed_images()):
            materialized.append((f"procedural_{index:02d}", image))

    dataset: list[BaselineDatasetItem] = []
    for seed_name, image in materialized:
        for variant_index in range(variants_per_seed):
            real_path = output_dir / "all" / "real" / f"{seed_name}_real_{variant_index:02d}.png"
            fake_path = output_dir / "all" / "fake" / f"{seed_name}_fake_{variant_index:02d}.png"
            save_image_bgr(real_path, _augment_real(image, rng))
            save_image_bgr(fake_path, _augment_fake(image, rng))
            dataset.append(BaselineDatasetItem(real_path, 0, seed_name))
            dataset.append(BaselineDatasetItem(fake_path, 1, seed_name))
    return dataset


def _persist_split_copy(items: Sequence[BaselineDatasetItem], split_dir: Path) -> None:
    for item in items:
        target_path = split_dir / ("fake" if item.label else "real") / item.image_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(item.image_path.read_bytes())


def train_and_evaluate_minimal_baseline(
    *,
    seed_dir: Path = DEFAULT_SEED_DIR,
    model_output_path: Path = DEFAULT_MODEL_OUTPUT_PATH,
    dataset_output_dir: Path = DEFAULT_DATASET_OUTPUT_DIR,
    eval_output_path: Path = DEFAULT_EVAL_OUTPUT_PATH,
    variants_per_seed: int = 6,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict:
    dataset = build_synthetic_dataset(
        seed_dir,
        dataset_output_dir,
        variants_per_seed=variants_per_seed,
        random_state=random_state,
    )
    if len(dataset) < 8:
        raise ValueError("synthetic dataset is too small to train the minimal baseline")

    train_items, test_items = train_test_split(
        dataset,
        test_size=test_size,
        random_state=random_state,
        stratify=[item.label for item in dataset],
    )
    _persist_split_copy(train_items, dataset_output_dir / "train")
    _persist_split_copy(test_items, dataset_output_dir / "test")

    train_x = np.vstack([extract_baseline_features(load_image_bgr(item.image_path)) for item in train_items])
    train_y = np.asarray([item.label for item in train_items], dtype=np.int64)
    test_x = np.vstack([extract_baseline_features(load_image_bgr(item.image_path)) for item in test_items])
    test_y = np.asarray([item.label for item in test_items], dtype=np.int64)

    estimator = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=500, random_state=random_state)),
        ]
    )
    estimator.fit(train_x, train_y)

    probabilities = estimator.predict_proba(test_x)[:, 1]
    predictions = (probabilities >= 0.5).astype(np.int64)
    accuracy = float((predictions == test_y).mean())

    bundle = {
        "estimator": estimator,
        "feature_names": FEATURE_NAMES,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed_dir": str(seed_dir),
        "dataset_output_dir": str(dataset_output_dir),
        "metrics": {
            "accuracy": accuracy,
            "train_size": int(len(train_items)),
            "test_size": int(len(test_items)),
        },
    }

    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    with model_output_path.open("wb") as handle:
        pickle.dump(bundle, handle)

    predictions_payload = [
        {
            "image_path": str(item.image_path),
            "label": int(item.label),
            "prediction": int(pred),
            "probability_fake": float(prob),
            "source_seed": item.source_seed,
        }
        for item, pred, prob in zip(test_items, predictions.tolist(), probabilities.tolist())
    ]
    evaluation_payload = {
        "status": "ok",
        "model_path": str(model_output_path),
        "dataset_output_dir": str(dataset_output_dir),
        "metrics": bundle["metrics"],
        "predictions": predictions_payload,
    }
    eval_output_path.parent.mkdir(parents=True, exist_ok=True)
    eval_output_path.write_text(json.dumps(evaluation_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return evaluation_payload


def load_baseline_bundle(model_path: Path) -> dict:
    with model_path.open("rb") as handle:
        return pickle.load(handle)


class TrainableBaselineMethod(DetectionMethod):
    category = "classification"
    evidence_type = "score"

    def __init__(self, method_name: str, model_path: str | Path) -> None:
        self.method_name = method_name
        self.model_path = Path(model_path)
        self._bundle: dict | None = None

    def _load_bundle(self) -> dict:
        if self._bundle is None:
            self._bundle = load_baseline_bundle(self.model_path)
        return self._bundle

    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        if not self.model_path.exists():
            return [self._failed_evidence(image, "baseline model file not found") for image in images]

        try:
            bundle = self._load_bundle()
            estimator = bundle["estimator"]
        except Exception as exc:
            return [self._failed_evidence(image, f"baseline model load failed: {exc}") for image in images]

        evidences: list[DetectionEvidence] = []
        for image in images:
            try:
                image_bgr = load_image_bgr(image.image_path)
                features = extract_baseline_features(image_bgr).reshape(1, -1)
                probability_fake = float(estimator.predict_proba(features)[0, 1])
                mask = build_baseline_mask(image_bgr)
                evidences.append(
                    DetectionEvidence(
                        evidence_id=f"{image.image_name}:{self.method_name}",
                        method=self.method_name,
                        category=self.category,
                        evidence_type=self.evidence_type,
                        suspicious=probability_fake >= context.threshold,
                        confidence=probability_fake,
                        summary=f"{self.method_name} baseline classifier probability: {probability_fake:.3f}",
                        artifacts={"mask": mask},
                        metadata={
                            "model_path": str(self.model_path),
                            "feature_names": bundle.get("feature_names", FEATURE_NAMES),
                            "bundle_metrics": bundle.get("metrics", {}),
                        },
                    )
                )
            except Exception as exc:
                evidences.append(self._failed_evidence(image, f"baseline inference failed: {exc}"))
        return evidences

    def _failed_evidence(self, image: ImageInput, message: str) -> DetectionEvidence:
        return DetectionEvidence(
            evidence_id=f"{image.image_name}:{self.method_name}",
            method=self.method_name,
            category=self.category,
            evidence_type=self.evidence_type,
            suspicious=False,
            confidence=0.0,
            summary=message,
            artifacts={"mask": np.zeros((2, 2), dtype=np.float32)},
            metadata={"model_path": str(self.model_path)},
        )
