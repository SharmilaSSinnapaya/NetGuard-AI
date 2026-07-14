"""NetGuard-AI Streamlit dashboard — metrics, live predictions, alert feed."""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "dashboard"))

from netguard.config import get_settings  # noqa: E402
from sample_flows import DEMO_FLOWS, demo_batch  # noqa: E402

settings = get_settings()
# Allow Docker / env override without editing YAML
API_BASE = (os.environ.get("NETGUARD_API_BASE_URL") or settings.dashboard.api_base_url).rstrip("/")
TITLE = settings.dashboard.title
REFRESH = settings.dashboard.refresh_seconds

st.set_page_config(
    page_title=TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Restrained ops-console styling (slate + teal; avoid generic purple AI theme)
st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(180deg, #0f1419 0%, #151b23 45%, #12171e 100%); }
      [data-testid="stSidebar"] { background-color: #0c1015; border-right: 1px solid #243041; }
      h1, h2, h3, p, label, span { color: #e7eef7 !important; }
      div[data-testid="stMetricValue"] { color: #5eead4 !important; }
      .alert-row { padding: 0.55rem 0.75rem; border-left: 3px solid #f59e0b;
                   background: rgba(245, 158, 11, 0.08); margin-bottom: 0.4rem; border-radius: 4px; }
      .ok-row { padding: 0.55rem 0.75rem; border-left: 3px solid #34d399;
                background: rgba(52, 211, 153, 0.07); margin-bottom: 0.4rem; border-radius: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str, timeout: float = 8.0) -> tuple[bool, dict | list | str]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{API_BASE}{path}")
            if resp.status_code >= 400:
                return False, f"HTTP {resp.status_code}: {resp.text[:300]}"
            return True, resp.json()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def api_predict(flows: list[dict], timeout: float = 15.0) -> tuple[bool, dict | str]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{API_BASE}/predict", json={"flows": flows})
            if resp.status_code >= 400:
                return False, f"HTTP {resp.status_code}: {resp.text[:300]}"
            return True, resp.json()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def init_state() -> None:
    if "events" not in st.session_state:
        st.session_state.events = []  # newest first
    if "category_counts" not in st.session_state:
        st.session_state.category_counts = Counter()
    if "total_scanned" not in st.session_state:
        st.session_state.total_scanned = 0
    if "total_attacks" not in st.session_state:
        st.session_state.total_attacks = 0
    if "total_anomalies" not in st.session_state:
        st.session_state.total_anomalies = 0


def record_predictions(demo_meta: list[dict], predictions: list[dict]) -> None:
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    for meta, pred in zip(demo_meta, predictions):
        event = {
            "time": now,
            "name": meta["name"],
            "hint": meta["expected_hint"],
            "category": pred.get("attack_category", "unknown"),
            "is_attack": bool(pred.get("is_attack")),
            "anomaly_flag": bool(pred.get("anomaly_flag")),
            "anomaly_score": float(pred.get("anomaly_score", 0.0)),
            "confidence": pred.get("confidence"),
        }
        st.session_state.events.insert(0, event)
        st.session_state.category_counts[event["category"]] += 1
        st.session_state.total_scanned += 1
        if event["is_attack"]:
            st.session_state.total_attacks += 1
        if event["anomaly_flag"]:
            st.session_state.total_anomalies += 1
    # Cap history for UI responsiveness
    st.session_state.events = st.session_state.events[:200]


init_state()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f"### {settings.project.name}")
    st.caption(settings.project.description)
    st.divider()
    st.text_input("API base URL", value=API_BASE, disabled=True)
    batch_size = st.slider("Flows per scan", min_value=1, max_value=len(DEMO_FLOWS), value=3)
    auto = st.toggle("Auto-scan", value=False, help=f"Re-run demo scan about every {REFRESH}s")
    scan_now = st.button("Scan demo traffic", type="primary", use_container_width=True)
    clear = st.button("Clear session feed", use_container_width=True)
    if clear:
        st.session_state.events = []
        st.session_state.category_counts = Counter()
        st.session_state.total_scanned = 0
        st.session_state.total_attacks = 0
        st.session_state.total_anomalies = 0
        st.rerun()

st.title(TITLE)
st.caption("Live view of supervised IDS + anomaly scores via the FastAPI inference service.")

# ---------- Health ----------
ok_health, health = api_get("/health")
c1, c2, c3, c4 = st.columns(4)
if ok_health and isinstance(health, dict):
    c1.metric("API status", str(health.get("status", "unknown")).upper())
    c2.metric("Models loaded", "Yes" if health.get("models_loaded") else "No")
    c3.metric("Flows scanned", st.session_state.total_scanned)
    c4.metric("Attacks flagged", st.session_state.total_attacks)
else:
    st.error(
        f"Cannot reach API at `{API_BASE}`. "
        "Start it with `run_step4.bat` or "
        "`uvicorn api.main:app --host 127.0.0.1 --port 8000`, then refresh."
    )
    st.stop()

# ---------- Metrics from training ----------
ok_metrics, metrics = api_get("/metrics")
left, right = st.columns((1.2, 1))

with left:
    st.subheader("Model performance (held-out NSL-KDD test)")
    if ok_metrics and isinstance(metrics, dict):
        supervised = metrics.get("supervised", {})
        anomaly = metrics.get("anomaly", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Supervised accuracy", f"{supervised.get('accuracy', 0):.3f}")
        m2.metric("Supervised F1 (weighted)", f"{supervised.get('f1_weighted', 0):.3f}")
        m3.metric("Anomaly ROC-AUC", f"{(anomaly.get('roc_auc') or 0):.3f}")

        report = supervised.get("classification_report") or {}
        rows = []
        for cls in ("normal", "dos", "probe", "r2l", "u2r"):
            if cls in report and isinstance(report[cls], dict):
                rows.append(
                    {
                        "class": cls,
                        "precision": report[cls].get("precision"),
                        "recall": report[cls].get("recall"),
                        "f1": report[cls].get("f1-score"),
                        "support": report[cls].get("support"),
                    }
                )
        if rows:
            fig = px.bar(
                pd.DataFrame(rows),
                x="class",
                y="f1",
                color="class",
                title="Per-class F1 (supervised)",
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e7eef7",
                showlegend=False,
                margin=dict(l=10, r=10, t=50, b=10),
                yaxis_title="F1",
                xaxis_title="",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Could not load /metrics: {metrics}")

with right:
    st.subheader("Session category mix")
    if st.session_state.category_counts:
        pie_df = pd.DataFrame(
            {
                "category": list(st.session_state.category_counts.keys()),
                "count": list(st.session_state.category_counts.values()),
            }
        )
        fig_pie = px.pie(
            pie_df,
            names="category",
            values="count",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e7eef7",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        st.metric("Anomaly flags (session)", st.session_state.total_anomalies)
    else:
        st.info("No scans yet. Click **Scan demo traffic** in the sidebar.")

# ---------- Scan actions ----------
should_scan = scan_now or auto
if should_scan:
    meta = DEMO_FLOWS[:batch_size]
    flows = [m["flow"] for m in meta]
    ok_pred, payload = api_predict(flows)
    if not ok_pred or not isinstance(payload, dict):
        st.error(f"Predict failed: {payload}")
    else:
        preds = payload.get("predictions", [])
        record_predictions(meta, preds)
        if scan_now:
            st.success(f"Scanned {len(preds)} flow(s).")

st.subheader("Alert / event feed")
if not st.session_state.events:
    st.caption("Events will appear here after a scan.")
else:
    for event in st.session_state.events[:25]:
        conf = event["confidence"]
        conf_s = f"{conf:.2f}" if isinstance(conf, float) else "n/a"
        line = (
            f"`{event['time']}` · **{event['name']}** → "
            f"`{event['category']}` · confidence {conf_s} · "
            f"anomaly_score {event['anomaly_score']:.3f}"
        )
        css = "alert-row" if event["is_attack"] or event["anomaly_flag"] else "ok-row"
        st.markdown(f"<div class='{css}'>{line}</div>", unsafe_allow_html=True)

    table = pd.DataFrame(st.session_state.events)
    st.dataframe(table, use_container_width=True, hide_index=True)

# Optional auto refresh (Streamlit rerun loop)
if auto:
    import time

    time.sleep(max(REFRESH, 1))
    st.rerun()
