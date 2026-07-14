"""Model training, evaluation, and artifact persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)

from netguard.config import Settings, get_settings
from netguard.preprocess import load_processed_bundle


@dataclass
class TrainResult:
    """Artifacts produced by a full training run."""

    supervised_model: Any | None
    anomaly_model: Any | None
    metrics: dict[str, Any]
    model_dir: Path


def build_supervised_model(settings: Settings):
    """Construct the configured supervised classifier."""
    cfg = settings.training.supervised
    algorithm = cfg.algorithm.lower()
    common = {
        "n_estimators": cfg.n_estimators,
        "max_depth": cfg.max_depth,
        "random_state": settings.training.random_state,
        "n_jobs": -1,
    }

    if algorithm == "random_forest":
        return RandomForestClassifier(
            class_weight=cfg.class_weight,
            **common,
        )

    if algorithm == "xgboost":
        from xgboost import XGBClassifier

        # XGBoost has no class_weight=string; scale via max_depth / default imbalance handling.
        return XGBClassifier(
            objective="multi:softprob",
            eval_metric="mlogloss",
            tree_method="hist",
            **common,
        )

    raise ValueError(
        f"Unsupported supervised algorithm: {cfg.algorithm!r}. "
        "Use 'random_forest' or 'xgboost'."
    )


def build_anomaly_model(settings: Settings) -> IsolationForest:
    """Construct Isolation Forest for unsupervised anomaly scoring."""
    cfg = settings.training.anomaly
    if cfg.algorithm.lower() != "isolation_forest":
        raise ValueError(
            f"Unsupported anomaly algorithm: {cfg.algorithm!r}. "
            "Use 'isolation_forest'."
        )
    return IsolationForest(
        n_estimators=cfg.n_estimators,
        contamination=cfg.contamination,
        random_state=settings.training.random_state,
        n_jobs=-1,
    )


def evaluate_supervised(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: list[str],
) -> dict[str, Any]:
    """Compute multi-class classification metrics on the held-out test set."""
    y_pred = model.predict(X_test)
    report = classification_report(
        y_test,
        y_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(
            f1_score(y_test, y_pred, average="weighted", zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": report,
    }


def evaluate_anomaly(
    model: IsolationForest,
    X_test: np.ndarray,
    y_test_binary: np.ndarray,
) -> dict[str, Any]:
    """
    Evaluate Isolation Forest against binary attack labels.

    sklearn IF: predict() returns 1 for inliers (normal) and -1 for outliers.
    We map outliers → attack (1) and inliers → normal (0).
    """
    raw_pred = model.predict(X_test)
    y_pred = np.where(raw_pred == -1, 1, 0).astype(np.int64)

    # Higher decision_function ≈ more normal; invert so higher score ≈ more anomalous
    anomaly_scores = (-model.decision_function(X_test)).astype(np.float64)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test_binary,
        y_pred,
        average="binary",
        zero_division=0,
    )

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test_binary, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "anomaly_rate_predicted": float(y_pred.mean()),
        "attack_rate_actual": float(y_test_binary.mean()),
    }

    # ROC-AUC needs both classes present in y_true
    if len(np.unique(y_test_binary)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_test_binary, anomaly_scores))
    else:
        metrics["roc_auc"] = None

    return metrics


def train_supervised(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: list[str],
    settings: Settings,
) -> tuple[Any, dict[str, Any]]:
    """Fit the supervised IDS model and return (model, metrics)."""
    model = build_supervised_model(settings)
    model.fit(X_train, y_train)
    metrics = evaluate_supervised(model, X_test, y_test, class_names)
    metrics["algorithm"] = settings.training.supervised.algorithm
    metrics["n_estimators"] = settings.training.supervised.n_estimators
    return model, metrics


def train_anomaly(
    X_train: np.ndarray,
    y_train_binary: np.ndarray,
    X_test: np.ndarray,
    y_test_binary: np.ndarray,
    settings: Settings,
) -> tuple[IsolationForest, dict[str, Any]]:
    """
    Fit Isolation Forest on normal traffic only, evaluate on the full test set.

    Training only on normals matches the IDS use-case: learn "benign" behavior,
    then flag deviations as potential attacks.
    """
    normal_mask = y_train_binary == 0
    if not np.any(normal_mask):
        raise ValueError("No normal samples available to train Isolation Forest")

    X_normal = X_train[normal_mask]
    model = build_anomaly_model(settings)
    model.fit(X_normal)
    metrics = evaluate_anomaly(model, X_test, y_test_binary)
    metrics["algorithm"] = settings.training.anomaly.algorithm
    metrics["n_estimators"] = settings.training.anomaly.n_estimators
    metrics["contamination"] = settings.training.anomaly.contamination
    metrics["n_normal_train"] = int(normal_mask.sum())
    return model, metrics


def save_training_artifacts(
    *,
    supervised_model: Any | None,
    anomaly_model: Any | None,
    metrics: dict[str, Any],
    settings: Settings,
) -> Path:
    """Write model binaries and metrics JSON under models/artifacts/."""
    model_dir = settings.resolve_path(settings.paths.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    if supervised_model is not None:
        path = model_dir / settings.api.model_name
        joblib.dump(supervised_model, path)

    if anomaly_model is not None:
        path = model_dir / settings.api.anomaly_model_name
        joblib.dump(anomaly_model, path)

    metrics_path = model_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return model_dir


def run_training(settings: Settings | None = None) -> TrainResult:
    """Load processed data, train enabled models, persist artifacts."""
    settings = settings or get_settings()
    processed_dir = settings.resolve_path(settings.paths.processed_data_dir)

    if not (processed_dir / "arrays.npz").exists():
        raise FileNotFoundError(
            f"Processed data not found in {processed_dir}. "
            "Run scripts/preprocess.py first (Step 2)."
        )

    data = load_processed_bundle(processed_dir)
    class_names = list(data["meta"].get("class_names") or data["label_encoder"].classes_)

    supervised_model = None
    anomaly_model = None
    metrics: dict[str, Any] = {
        "project": settings.project.name,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_meta": {
            "n_train": data["meta"].get("n_train"),
            "n_test": data["meta"].get("n_test"),
            "n_features": data["meta"].get("n_features"),
            "class_counts_train": data["meta"].get("class_counts_train"),
            "class_counts_test": data["meta"].get("class_counts_test"),
        },
    }

    if settings.training.supervised.enabled:
        supervised_model, supervised_metrics = train_supervised(
            data["X_train"],
            data["y_train"],
            data["X_test"],
            data["y_test"],
            class_names,
            settings,
        )
        metrics["supervised"] = supervised_metrics

    if settings.training.anomaly.enabled:
        anomaly_model, anomaly_metrics = train_anomaly(
            data["X_train"],
            data["y_train_binary"],
            data["X_test"],
            data["y_test_binary"],
            settings,
        )
        metrics["anomaly"] = anomaly_metrics

    model_dir = save_training_artifacts(
        supervised_model=supervised_model,
        anomaly_model=anomaly_model,
        metrics=metrics,
        settings=settings,
    )

    return TrainResult(
        supervised_model=supervised_model,
        anomaly_model=anomaly_model,
        metrics=metrics,
        model_dir=model_dir,
    )
