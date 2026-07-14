"""Run NSL-KDD preprocessing and write artifacts to data/processed/."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netguard.preprocess import run_preprocessing_pipeline


def main() -> int:
    bundle = run_preprocessing_pipeline()
    print("[ok] preprocessing complete")
    print(f"  train samples : {bundle.meta['n_train']}")
    print(f"  test samples  : {bundle.meta['n_test']}")
    print(f"  features      : {bundle.meta['n_features']}")
    print(f"  train classes : {bundle.meta['class_counts_train']}")
    print(f"  test classes  : {bundle.meta['class_counts_test']}")
    print("  artifacts     : data/processed/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
