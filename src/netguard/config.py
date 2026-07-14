"""Load NetGuard-AI configuration from config/settings.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "settings.yaml"


class ProjectConfig(BaseModel):
    name: str
    version: str
    description: str


class PathsConfig(BaseModel):
    raw_data_dir: str
    processed_data_dir: str
    model_dir: str
    logs_dir: str


class DatasetConfig(BaseModel):
    name: str
    train_file: str
    test_file: str
    target_column: str
    label_column: str
    download_urls: dict[str, str] = Field(default_factory=dict)


class FeaturesConfig(BaseModel):
    categorical: list[str]
    drop_columns: list[str]


class SupervisedConfig(BaseModel):
    enabled: bool = True
    algorithm: str = "random_forest"
    n_estimators: int = 100
    max_depth: int | None = None
    class_weight: str | None = "balanced"


class AnomalyConfig(BaseModel):
    enabled: bool = True
    algorithm: str = "isolation_forest"
    contamination: float = 0.1
    n_estimators: int = 100


class TrainingConfig(BaseModel):
    random_state: int = 42
    test_size: float = 0.2
    supervised: SupervisedConfig = Field(default_factory=SupervisedConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    model_name: str = "supervised_ids.joblib"
    anomaly_model_name: str = "anomaly_iforest.joblib"


class DashboardConfig(BaseModel):
    api_base_url: str = "http://127.0.0.1:8000"
    refresh_seconds: int = 2
    title: str = "NetGuard-AI Dashboard"


class Settings(BaseModel):
    project: ProjectConfig
    paths: PathsConfig
    dataset: DatasetConfig
    features: FeaturesConfig
    training: TrainingConfig
    api: ApiConfig
    dashboard: DashboardConfig

    def resolve_path(self, relative: str) -> Path:
        """Resolve a project-relative path against the repo root."""
        path = Path(relative)
        return path if path.is_absolute() else ROOT_DIR / path


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} must be a mapping")
    return data


@lru_cache(maxsize=1)
def get_settings(config_path: str | None = None) -> Settings:
    """Return cached Settings loaded from YAML."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    return Settings.model_validate(_load_yaml(path))
