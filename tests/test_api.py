"""API and inference unit tests (synthetic artifacts; no full NSL-KDD needed)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

import joblib

from netguard.labels import ATTACK_CATEGORIES, FEATURE_COLUMNS
from netguard.predict import clear_model_cache, records_to_dataframe


def _build_tiny_artifacts(tmp_path: Path) -> Path:
    """Create minimal preprocessor + models + metrics under tmp_path."""
    processed = tmp_path / "processed"
    models = tmp_path / "models"
    processed.mkdir()
    models.mkdir()

    # Tiny synthetic training matrix with categoricals + numerics
    n = 40
    protocols = np.random.default_rng(0).choice(["tcp", "udp", "icmp"], size=n)
    services = np.random.default_rng(1).choice(["http", "private", "ftp"], size=n)
    flags = np.random.default_rng(2).choice(["SF", "S0", "REJ"], size=n)

    import pandas as pd

    data = {col: np.zeros(n) for col in FEATURE_COLUMNS}
    data["protocol_type"] = protocols
    data["service"] = services
    data["flag"] = flags
    data["src_bytes"] = np.random.default_rng(3).integers(0, 500, size=n)
    data["dst_bytes"] = np.random.default_rng(4).integers(0, 500, size=n)
    data["count"] = np.random.default_rng(5).integers(1, 50, size=n)
    df = pd.DataFrame(data)

    categorical = ["protocol_type", "service", "flag"]
    numeric = [c for c in FEATURE_COLUMNS if c not in categorical]
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
            ("num", StandardScaler(), numeric),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    X = preprocessor.fit_transform(df)

    y_names = np.random.default_rng(6).choice(list(ATTACK_CATEGORIES), size=n)
    label_encoder = LabelEncoder()
    label_encoder.fit(list(ATTACK_CATEGORIES))
    y = label_encoder.transform(y_names)

    clf = RandomForestClassifier(n_estimators=10, random_state=42)
    clf.fit(X, y)

    normal_mask = y_names == "normal"
    if not normal_mask.any():
        normal_mask[0] = True
    iforest = IsolationForest(n_estimators=10, contamination=0.2, random_state=42)
    iforest.fit(X[normal_mask])

    joblib.dump(preprocessor, processed / "preprocessor.joblib")
    joblib.dump(label_encoder, processed / "label_encoder.joblib")
    joblib.dump(list(preprocessor.get_feature_names_out()), processed / "feature_names.joblib")
    joblib.dump(clf, models / "supervised_ids.joblib")
    joblib.dump(iforest, models / "anomaly_iforest.joblib")
    (models / "metrics.json").write_text(
        json.dumps({"supervised": {"accuracy": 0.9}, "anomaly": {"f1": 0.5}}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _build_tiny_artifacts(tmp_path)
    # Point config paths at the temp artifacts by patching get_settings result
    from netguard import config as config_mod
    from netguard import predict as predict_mod

    # Keep a handle to the real cached function BEFORE monkeypatching
    real_get_settings = config_mod.get_settings
    real_get_settings.cache_clear()
    clear_model_cache()

    base = real_get_settings()
    patched = base.model_copy(
        update={
            "paths": base.paths.model_copy(
                update={
                    "processed_data_dir": str(root / "processed"),
                    "model_dir": str(root / "models"),
                }
            )
        }
    )

    def _patched_settings(config_path: str | None = None):
        return patched

    monkeypatch.setattr(config_mod, "get_settings", _patched_settings)
    monkeypatch.setattr(predict_mod, "get_settings", _patched_settings)

    # api.main captured settings at import — reload app with patched settings
    import importlib
    import api.main as api_main

    importlib.reload(api_main)
    clear_model_cache()
    client = TestClient(api_main.app)
    yield client
    clear_model_cache()
    # Do NOT call .cache_clear() on the monkeypatched function (it is a plain def).
    real_get_settings.cache_clear()


def test_records_to_dataframe_defaults() -> None:
    df = records_to_dataframe(
        [{"protocol_type": "tcp", "service": "http", "flag": "SF", "src_bytes": 10}]
    )
    assert list(df.columns) == FEATURE_COLUMNS
    assert df.loc[0, "src_bytes"] == 10
    assert df.loc[0, "dst_bytes"] == 0


def test_health_and_metrics(api_env: TestClient) -> None:
    health = api_env.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["models_loaded"] is True
    assert body["status"] == "ok"

    metrics = api_env.get("/metrics")
    assert metrics.status_code == 200
    assert "supervised" in metrics.json()


def test_predict_endpoint(api_env: TestClient) -> None:
    payload = {
        "flows": [
            {
                "protocol_type": "tcp",
                "service": "http",
                "flag": "SF",
                "src_bytes": 100,
                "dst_bytes": 200,
                "count": 5,
            }
        ]
    }
    resp = api_env.post("/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    pred = data["predictions"][0]
    assert pred["attack_category"] in ATTACK_CATEGORIES
    assert "anomaly_score" in pred
    assert "class_probabilities" in pred
