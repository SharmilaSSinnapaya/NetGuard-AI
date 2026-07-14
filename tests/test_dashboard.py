"""Lightweight checks for dashboard helpers (no Streamlit runtime required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from sample_flows import DEMO_FLOWS, demo_batch
from netguard.labels import FEATURE_COLUMNS


def test_demo_flows_have_required_fields() -> None:
    assert len(DEMO_FLOWS) >= 4
    for item in DEMO_FLOWS:
        assert "name" in item and "flow" in item
        flow = item["flow"]
        for key in ("protocol_type", "service", "flag"):
            assert key in flow
        # All feature columns present for API compatibility
        for col in FEATURE_COLUMNS:
            assert col in flow


def test_demo_batch_limit() -> None:
    batch = demo_batch(2)
    assert len(batch) == 2
    assert isinstance(batch[0], dict)
