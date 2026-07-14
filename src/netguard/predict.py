"""Inference helpers for supervised and anomaly models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from netguard.config import Settings, get_settings
from netguard.labels import FEATURE_COLUMNS


@dataclass
class ModelBundle:
    """Loaded runtime artifacts for inference."""

    supervised_model: Any
    anomaly_model: Any
    preprocessor: Any
    label_encoder: Any
    feature_names: list[str]
    metrics: dict[str, Any]
    settings: Settings


@lru_cache(maxsize=1)
def load_model_bundle(config_path: str | None = None) -> ModelBundle:
    """Load preprocessor + models + metrics once (cached)."""
    settings = get_settings(config_path)
    processed_dir = settings.resolve_path(settings.paths.processed_data_dir)
    model_dir = settings.resolve_path(settings.paths.model_dir)

    supervised_path = model_dir / settings.api.model_name
    anomaly_path = model_dir / settings.api.anomaly_model_name
    preprocessor_path = processed_dir / "preprocessor.joblib"
    label_encoder_path = processed_dir / "label_encoder.joblib"
    feature_names_path = processed_dir / "feature_names.joblib"
    metrics_path = model_dir / "metrics.json"

    missing = [
        str(p)
        for p in (
            supervised_path,
            anomaly_path,
            preprocessor_path,
            label_encoder_path,
        )
        if not p.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing required artifacts:\n  - "
            + "\n  - ".join(missing)
            + "\nRun Steps 2–3 (preprocess + train) first."
        )

    feature_names: list[str]
    if feature_names_path.exists():
        feature_names = list(joblib.load(feature_names_path))
    else:
        feature_names = []

    metrics: dict[str, Any] = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    return ModelBundle(
        supervised_model=joblib.load(supervised_path),
        anomaly_model=joblib.load(anomaly_path),
        preprocessor=joblib.load(preprocessor_path),
        label_encoder=joblib.load(label_encoder_path),
        feature_names=feature_names,
        metrics=metrics,
        settings=settings,
    )


def clear_model_cache() -> None:
    """Drop cached models (useful in tests)."""
    load_model_bundle.cache_clear()


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Build a feature DataFrame from raw NSL-KDD-style field dicts.

    Accepts the 41 network features (or a subset); missing numeric fields
    default to 0. Categorical fields must be provided for meaningful results.
    """
    rows: list[dict[str, Any]] = []
    for record in records:
        row = {col: record.get(col, 0) for col in FEATURE_COLUMNS}
        # Ensure categoricals are strings
        for cat in ("protocol_type", "service", "flag"):
            row[cat] = str(row[cat])
        rows.append(row)
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def transform_features(bundle: ModelBundle, df: pd.DataFrame) -> np.ndarray:
    """Apply the fitted preprocessor to raw feature rows."""
    return np.asarray(bundle.preprocessor.transform(df), dtype=np.float64)


def predict_batch(
    records: list[dict[str, Any]],
    bundle: ModelBundle | None = None,
) -> list[dict[str, Any]]:
    """
    Run supervised + anomaly inference on one or more flow records.

    Returns per-row predictions with class probabilities and anomaly score.
    """
    if not records:
        return []

    bundle = bundle or load_model_bundle()
    df = records_to_dataframe(records)
    X = transform_features(bundle, df)

    class_ids = bundle.supervised_model.predict(X)
    class_names = bundle.label_encoder.inverse_transform(class_ids)

    probabilities: np.ndarray | None = None
    if hasattr(bundle.supervised_model, "predict_proba"):
        probabilities = bundle.supervised_model.predict_proba(X)

    raw_anomaly = bundle.anomaly_model.predict(X)
    # sklearn: -1 outlier / attack, 1 inlier / normal
    is_anomaly = (raw_anomaly == -1).astype(int)
    anomaly_scores = (-bundle.anomaly_model.decision_function(X)).astype(np.float64)

    results: list[dict[str, Any]] = []
    for i, name in enumerate(class_names):
        item: dict[str, Any] = {
            "attack_category": str(name),
            "is_attack": bool(name != "normal"),
            "anomaly_flag": bool(is_anomaly[i]),
            "anomaly_score": float(anomaly_scores[i]),
        }
        if probabilities is not None:
            proba_map = {
                str(cls): float(probabilities[i, j])
                for j, cls in enumerate(bundle.label_encoder.classes_)
            }
            item["class_probabilities"] = proba_map
            item["confidence"] = float(max(proba_map.values()))
        results.append(item)
    return results
