"""Unit tests for model training (synthetic data; no NSL-KDD download required)."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.datasets import make_classification
from sklearn.preprocessing import LabelEncoder

from netguard.config import get_settings
from netguard.labels import ATTACK_CATEGORIES
from netguard.train import (
    build_anomaly_model,
    build_supervised_model,
    evaluate_anomaly,
    evaluate_supervised,
    run_training,
    save_training_artifacts,
    train_anomaly,
    train_supervised,
)


@pytest.fixture
def synthetic_multiclass() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    X, y = make_classification(
        n_samples=300,
        n_features=20,
        n_informative=12,
        n_redundant=4,
        n_classes=5,
        n_clusters_per_class=1,
        random_state=42,
    )
    class_names = list(ATTACK_CATEGORIES)
    encoder = LabelEncoder()
    encoder.fit(class_names)
    # Map synthetic ints 0..4 onto attack category names, then to encoded ids
    y = encoder.transform(np.array(class_names)[y])
    split = 220
    return X[:split], y[:split], X[split:], y[split:], list(encoder.classes_)


@pytest.fixture
def synthetic_binary(
    synthetic_multiclass: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X_train, y_train, X_test, y_test, class_names = synthetic_multiclass
    normal_idx = list(class_names).index("normal")
    y_train_bin = (y_train != normal_idx).astype(np.int64)
    y_test_bin = (y_test != normal_idx).astype(np.int64)
    return X_train, y_train_bin, X_test, y_test_bin


def _fast_settings(**path_overrides: str):
    settings = get_settings()
    supervised = settings.training.supervised.model_copy(update={"n_estimators": 20})
    anomaly = settings.training.anomaly.model_copy(
        update={"n_estimators": 30, "contamination": 0.15}
    )
    training = settings.training.model_copy(
        update={"supervised": supervised, "anomaly": anomaly}
    )
    updates: dict = {"training": training}
    if path_overrides:
        updates["paths"] = settings.paths.model_copy(update=path_overrides)
    return settings.model_copy(update=updates)


def test_build_supervised_random_forest() -> None:
    model = build_supervised_model(get_settings())
    assert model.__class__.__name__ == "RandomForestClassifier"


def test_build_anomaly_isolation_forest() -> None:
    model = build_anomaly_model(get_settings())
    assert model.__class__.__name__ == "IsolationForest"


def test_train_and_evaluate_supervised(synthetic_multiclass) -> None:
    X_train, y_train, X_test, y_test, class_names = synthetic_multiclass
    settings = _fast_settings()

    model, metrics = train_supervised(
        X_train, y_train, X_test, y_test, class_names, settings
    )
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert "confusion_matrix" in metrics
    assert model.predict(X_test[:5]).shape == (5,)

    again = evaluate_supervised(model, X_test, y_test, class_names)
    assert again["accuracy"] == metrics["accuracy"]


def test_train_and_evaluate_anomaly(synthetic_binary) -> None:
    X_train, y_train_bin, X_test, y_test_bin = synthetic_binary
    settings = _fast_settings()

    model, metrics = train_anomaly(
        X_train, y_train_bin, X_test, y_test_bin, settings
    )
    assert "f1" in metrics
    assert "roc_auc" in metrics
    assert metrics["n_normal_train"] > 0

    again = evaluate_anomaly(model, X_test, y_test_bin)
    assert again["accuracy"] == metrics["accuracy"]


def test_save_artifacts(tmp_path: Path, synthetic_multiclass) -> None:
    X_train, y_train, X_test, y_test, class_names = synthetic_multiclass
    settings = _fast_settings(model_dir=str(tmp_path / "artifacts"))

    supervised, s_metrics = train_supervised(
        X_train, y_train, X_test, y_test, class_names, settings
    )
    normal_idx = list(class_names).index("normal")
    y_train_bin = (y_train != normal_idx).astype(np.int64)
    y_test_bin = (y_test != normal_idx).astype(np.int64)
    anomaly, a_metrics = train_anomaly(
        X_train, y_train_bin, X_test, y_test_bin, settings
    )

    out = save_training_artifacts(
        supervised_model=supervised,
        anomaly_model=anomaly,
        metrics={"supervised": s_metrics, "anomaly": a_metrics},
        settings=settings,
    )
    assert (out / settings.api.model_name).exists()
    assert (out / settings.api.anomaly_model_name).exists()
    assert (out / "metrics.json").exists()
    loaded = joblib.load(out / settings.api.model_name)
    assert loaded.predict(X_test[:3]).shape == (3,)
    payload = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert "supervised" in payload


def test_run_training_requires_processed_data(tmp_path: Path) -> None:
    settings = _fast_settings(
        processed_data_dir=str(tmp_path / "missing"),
        model_dir=str(tmp_path / "models"),
    )
    with pytest.raises(FileNotFoundError):
        run_training(settings)
