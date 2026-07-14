"""Unit tests for NSL-KDD labels and preprocessing (no network required)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from netguard.labels import (
    ATTACK_CATEGORIES,
    NSL_KDD_COLUMNS,
    label_to_category,
    normalize_label,
)
from netguard.preprocess import (
    add_attack_category,
    fit_transform_split,
    load_nsl_kdd_csv,
    save_processed_bundle,
    load_processed_bundle,
)


def _sample_row(
    protocol: str = "tcp",
    service: str = "http",
    flag: str = "SF",
    label: str = "normal",
    difficulty: int = 20,
) -> list:
    """Build one synthetic NSL-KDD-style row (43 fields)."""
    row: list = [0] * len(NSL_KDD_COLUMNS)
    row[NSL_KDD_COLUMNS.index("protocol_type")] = protocol
    row[NSL_KDD_COLUMNS.index("service")] = service
    row[NSL_KDD_COLUMNS.index("flag")] = flag
    row[NSL_KDD_COLUMNS.index("src_bytes")] = 100
    row[NSL_KDD_COLUMNS.index("dst_bytes")] = 200
    row[NSL_KDD_COLUMNS.index("label")] = label
    row[NSL_KDD_COLUMNS.index("difficulty")] = difficulty
    return row


@pytest.fixture
def tiny_raw_files(tmp_path: Path) -> tuple[Path, Path]:
    train = pd.DataFrame(
        [
            _sample_row(label="normal"),
            _sample_row(label="neptune", protocol="tcp", service="private"),
            _sample_row(label="satan", protocol="icmp", service="eco_i"),
            _sample_row(label="guess_passwd", service="telnet"),
            _sample_row(label="buffer_overflow", service="telnet"),
            _sample_row(label="normal", service="ftp"),
            _sample_row(label="smurf", protocol="icmp", service="ecr_i"),
            _sample_row(label="portsweep", service="private"),
        ],
        columns=NSL_KDD_COLUMNS,
    )
    test = pd.DataFrame(
        [
            _sample_row(label="normal"),
            _sample_row(label="neptune"),
            _sample_row(label="nmap", service="private"),
            # Unseen categorical value exercises handle_unknown='ignore'
            _sample_row(label="normal", service="domain_u"),
        ],
        columns=NSL_KDD_COLUMNS,
    )
    train_path = tmp_path / "KDDTrain+.txt"
    test_path = tmp_path / "KDDTest+.txt"
    train.to_csv(train_path, header=False, index=False)
    test.to_csv(test_path, header=False, index=False)
    return train_path, test_path


def test_normalize_label_strips_dot() -> None:
    assert normalize_label("Neptune.") == "neptune"


def test_label_to_category_mapping() -> None:
    assert label_to_category("normal") == "normal"
    assert label_to_category("neptune") == "dos"
    assert label_to_category("satan") == "probe"
    assert label_to_category("guess_passwd") == "r2l"
    assert label_to_category("buffer_overflow") == "u2r"


def test_unknown_label_raises() -> None:
    with pytest.raises(KeyError):
        label_to_category("not_a_real_attack")


def test_load_and_category(tiny_raw_files: tuple[Path, Path]) -> None:
    train_path, _ = tiny_raw_files
    df = load_nsl_kdd_csv(train_path)
    assert list(df.columns) == NSL_KDD_COLUMNS
    enriched = add_attack_category(df)
    assert set(enriched["attack_category"]) <= set(ATTACK_CATEGORIES)
    assert enriched["is_attack"].isin([0, 1]).all()


def test_fit_transform_and_persist(
    tiny_raw_files: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    train_path, test_path = tiny_raw_files
    train_df = load_nsl_kdd_csv(train_path)
    test_df = load_nsl_kdd_csv(test_path)

    bundle = fit_transform_split(train_df, test_df)
    assert bundle.X_train.shape[0] == len(train_df)
    assert bundle.X_test.shape[0] == len(test_df)
    assert bundle.X_train.shape[1] == bundle.X_test.shape[1]
    assert bundle.X_train.shape[1] == len(bundle.feature_names)
    assert set(bundle.class_names) == set(ATTACK_CATEGORIES)

    out = tmp_path / "processed"
    save_processed_bundle(bundle, out)
    loaded = load_processed_bundle(out)
    assert loaded["X_train"].shape == bundle.X_train.shape
    assert loaded["meta"]["n_features"] == bundle.meta["n_features"]
    assert (out / "preprocessor.joblib").exists()
    assert (out / "meta.json").exists()
