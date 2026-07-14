"""Data loading and feature preprocessing for NSL-KDD."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from netguard.config import Settings, get_settings
from netguard.labels import (
    ATTACK_CATEGORIES,
    FEATURE_COLUMNS,
    NSL_KDD_COLUMNS,
    label_to_category,
)


@dataclass
class ProcessedBundle:
    """In-memory result of the preprocessing pipeline."""

    X_train: np.ndarray
    y_train: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    y_train_binary: np.ndarray
    y_test_binary: np.ndarray
    feature_names: list[str]
    class_names: list[str]
    preprocessor: ColumnTransformer
    label_encoder: LabelEncoder
    meta: dict[str, Any]


def load_nsl_kdd_csv(path: Path) -> pd.DataFrame:
    """Load an NSL-KDD .txt/.csv file (no header) into a named DataFrame."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    df = pd.read_csv(path, header=None, names=NSL_KDD_COLUMNS)
    if df.shape[1] != len(NSL_KDD_COLUMNS):
        raise ValueError(
            f"Expected {len(NSL_KDD_COLUMNS)} columns in {path.name}, got {df.shape[1]}"
        )
    return df


def add_attack_category(df: pd.DataFrame) -> pd.DataFrame:
    """Append coarse attack_category and binary is_attack columns."""
    out = df.copy()
    out["attack_category"] = out["label"].map(label_to_category)
    out["is_attack"] = (out["attack_category"] != "normal").astype(int)
    return out


def build_preprocessor(
    categorical_columns: list[str],
    numeric_columns: list[str],
) -> ColumnTransformer:
    """Build a ColumnTransformer: one-hot categoricals + scaled numerics."""
    # handle_unknown='ignore' keeps train/test feature dims aligned when rare
    # services appear only in the test set (common with NSL-KDD).
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_columns,
            ),
            ("num", StandardScaler(), numeric_columns),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def _feature_frame(df: pd.DataFrame, drop_columns: list[str]) -> pd.DataFrame:
    cols = [c for c in FEATURE_COLUMNS if c not in drop_columns]
    return df[cols].copy()


def fit_transform_split(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    settings: Settings | None = None,
) -> ProcessedBundle:
    """Fit encoders on train, transform train/test, return a ProcessedBundle."""
    settings = settings or get_settings()
    train = add_attack_category(train_df)
    test = add_attack_category(test_df)

    drop_columns = list(settings.features.drop_columns)
    categorical = [
        c for c in settings.features.categorical if c not in drop_columns
    ]
    X_train_df = _feature_frame(train, drop_columns)
    X_test_df = _feature_frame(test, drop_columns)
    numeric = [c for c in X_train_df.columns if c not in categorical]

    preprocessor = build_preprocessor(categorical, numeric)
    X_train = preprocessor.fit_transform(X_train_df)
    X_test = preprocessor.transform(X_test_df)

    label_encoder = LabelEncoder()
    label_encoder.fit(list(ATTACK_CATEGORIES))
    y_train = label_encoder.transform(train["attack_category"])
    y_test = label_encoder.transform(test["attack_category"])

    feature_names = list(preprocessor.get_feature_names_out())
    meta = {
        "n_train": int(X_train.shape[0]),
        "n_test": int(X_test.shape[0]),
        "n_features": int(X_train.shape[1]),
        "categorical_columns": categorical,
        "numeric_columns": numeric,
        "class_counts_train": train["attack_category"].value_counts().to_dict(),
        "class_counts_test": test["attack_category"].value_counts().to_dict(),
    }

    return ProcessedBundle(
        X_train=np.asarray(X_train, dtype=np.float64),
        y_train=np.asarray(y_train, dtype=np.int64),
        X_test=np.asarray(X_test, dtype=np.float64),
        y_test=np.asarray(y_test, dtype=np.int64),
        y_train_binary=train["is_attack"].to_numpy(dtype=np.int64),
        y_test_binary=test["is_attack"].to_numpy(dtype=np.int64),
        feature_names=feature_names,
        class_names=list(label_encoder.classes_),
        preprocessor=preprocessor,
        label_encoder=label_encoder,
        meta=meta,
    )


def save_processed_bundle(bundle: ProcessedBundle, output_dir: Path) -> Path:
    """Persist arrays, encoders, and metadata under data/processed/."""
    output_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output_dir / "arrays.npz",
        X_train=bundle.X_train,
        y_train=bundle.y_train,
        X_test=bundle.X_test,
        y_test=bundle.y_test,
        y_train_binary=bundle.y_train_binary,
        y_test_binary=bundle.y_test_binary,
    )
    joblib.dump(bundle.preprocessor, output_dir / "preprocessor.joblib")
    joblib.dump(bundle.label_encoder, output_dir / "label_encoder.joblib")
    joblib.dump(bundle.feature_names, output_dir / "feature_names.joblib")

    meta = {
        **bundle.meta,
        "class_names": bundle.class_names,
        "feature_names_count": len(bundle.feature_names),
    }
    (output_dir / "meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )
    return output_dir


def load_processed_bundle(processed_dir: Path) -> dict[str, Any]:
    """Load previously saved preprocessing artifacts."""
    arrays = np.load(processed_dir / "arrays.npz")
    return {
        "X_train": arrays["X_train"],
        "y_train": arrays["y_train"],
        "X_test": arrays["X_test"],
        "y_test": arrays["y_test"],
        "y_train_binary": arrays["y_train_binary"],
        "y_test_binary": arrays["y_test_binary"],
        "preprocessor": joblib.load(processed_dir / "preprocessor.joblib"),
        "label_encoder": joblib.load(processed_dir / "label_encoder.joblib"),
        "feature_names": joblib.load(processed_dir / "feature_names.joblib"),
        "meta": json.loads((processed_dir / "meta.json").read_text(encoding="utf-8")),
    }


def run_preprocessing_pipeline(settings: Settings | None = None) -> ProcessedBundle:
    """Download-ready end-to-end: load raw files → transform → save."""
    settings = settings or get_settings()
    raw_dir = settings.resolve_path(settings.paths.raw_data_dir)
    processed_dir = settings.resolve_path(settings.paths.processed_data_dir)

    train_path = raw_dir / settings.dataset.train_file
    test_path = raw_dir / settings.dataset.test_file

    train_df = load_nsl_kdd_csv(train_path)
    test_df = load_nsl_kdd_csv(test_path)
    bundle = fit_transform_split(train_df, test_df, settings=settings)
    save_processed_bundle(bundle, processed_dir)
    return bundle
