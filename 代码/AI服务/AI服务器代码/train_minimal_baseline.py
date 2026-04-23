from __future__ import annotations

import argparse
import json
from pathlib import Path

from detection_service.minimal_baseline import (
    DEFAULT_DATASET_OUTPUT_DIR,
    DEFAULT_EVAL_OUTPUT_PATH,
    DEFAULT_MODEL_OUTPUT_PATH,
    DEFAULT_SEED_DIR,
    train_and_evaluate_minimal_baseline,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the minimal runnable AI baseline.")
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--model-output", type=Path, default=DEFAULT_MODEL_OUTPUT_PATH)
    parser.add_argument("--dataset-output", type=Path, default=DEFAULT_DATASET_OUTPUT_DIR)
    parser.add_argument("--eval-output", type=Path, default=DEFAULT_EVAL_OUTPUT_PATH)
    parser.add_argument("--variants-per-seed", type=int, default=6)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    result = train_and_evaluate_minimal_baseline(
        seed_dir=args.seed_dir,
        model_output_path=args.model_output,
        dataset_output_dir=args.dataset_output,
        eval_output_path=args.eval_output,
        variants_per_seed=args.variants_per_seed,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
