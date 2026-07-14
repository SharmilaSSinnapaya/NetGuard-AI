"""Basic config load smoke test (expanded in later steps)."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netguard.config import get_settings


def test_settings_load() -> None:
    settings = get_settings()
    assert settings.project.name == "NetGuard-AI"
    assert settings.training.supervised.enabled is True
    assert settings.training.anomaly.enabled is True
    assert settings.dataset.name == "nsl-kdd"
