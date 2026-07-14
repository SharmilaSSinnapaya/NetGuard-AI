"""Curated demo flows for the NetGuard-AI dashboard (NSL-KDD-style features)."""

from __future__ import annotations

from typing import Any


def _base(**overrides: Any) -> dict[str, Any]:
    flow: dict[str, Any] = {
        "duration": 0,
        "protocol_type": "tcp",
        "service": "http",
        "flag": "SF",
        "src_bytes": 200,
        "dst_bytes": 800,
        "land": 0,
        "wrong_fragment": 0,
        "urgent": 0,
        "hot": 0,
        "num_failed_logins": 0,
        "logged_in": 1,
        "num_compromised": 0,
        "root_shell": 0,
        "su_attempted": 0,
        "num_root": 0,
        "num_file_creations": 0,
        "num_shells": 0,
        "num_access_files": 0,
        "num_outbound_cmds": 0,
        "is_host_login": 0,
        "is_guest_login": 0,
        "count": 2,
        "srv_count": 2,
        "serror_rate": 0.0,
        "srv_serror_rate": 0.0,
        "rerror_rate": 0.0,
        "srv_rerror_rate": 0.0,
        "same_srv_rate": 1.0,
        "diff_srv_rate": 0.0,
        "srv_diff_host_rate": 0.0,
        "dst_host_count": 20,
        "dst_host_srv_count": 20,
        "dst_host_same_srv_rate": 1.0,
        "dst_host_diff_srv_rate": 0.0,
        "dst_host_same_src_port_rate": 0.05,
        "dst_host_srv_diff_host_rate": 0.0,
        "dst_host_serror_rate": 0.0,
        "dst_host_srv_serror_rate": 0.0,
        "dst_host_rerror_rate": 0.0,
        "dst_host_srv_rerror_rate": 0.0,
    }
    flow.update(overrides)
    return flow


# Labeled for UI context only — model may disagree; that's part of the demo.
DEMO_FLOWS: list[dict[str, Any]] = [
    {
        "name": "Benign HTTP browse",
        "expected_hint": "normal",
        "flow": _base(src_bytes=315, dst_bytes=4120, logged_in=1, count=3),
    },
    {
        "name": "Neptune-like SYN flood",
        "expected_hint": "dos",
        "flow": _base(
            service="private",
            flag="S0",
            src_bytes=0,
            dst_bytes=0,
            logged_in=0,
            count=200,
            srv_count=200,
            serror_rate=1.0,
            srv_serror_rate=1.0,
            same_srv_rate=1.0,
            dst_host_count=255,
            dst_host_srv_count=255,
            dst_host_serror_rate=1.0,
            dst_host_srv_serror_rate=1.0,
        ),
    },
    {
        "name": "Port sweep pattern",
        "expected_hint": "probe",
        "flow": _base(
            service="private",
            flag="REJ",
            src_bytes=0,
            dst_bytes=0,
            logged_in=0,
            count=1,
            srv_count=1,
            rerror_rate=1.0,
            diff_srv_rate=1.0,
            dst_host_count=255,
            dst_host_srv_count=1,
            dst_host_diff_srv_rate=1.0,
            dst_host_same_src_port_rate=1.0,
            dst_host_rerror_rate=1.0,
        ),
    },
    {
        "name": "Guess-password style",
        "expected_hint": "r2l",
        "flow": _base(
            service="telnet",
            flag="SF",
            src_bytes=125,
            dst_bytes=180,
            logged_in=0,
            num_failed_logins=5,
            is_guest_login=1,
            count=1,
            hot=1,
        ),
    },
    {
        "name": "Buffer overflow-ish",
        "expected_hint": "u2r",
        "flow": _base(
            service="telnet",
            flag="SF",
            src_bytes=1500,
            dst_bytes=0,
            logged_in=1,
            root_shell=1,
            num_compromised=3,
            num_root=2,
            num_file_creations=1,
            hot=3,
        ),
    },
    {
        "name": "ICMP echo volume",
        "expected_hint": "dos",
        "flow": _base(
            protocol_type="icmp",
            service="ecr_i",
            flag="SF",
            src_bytes=1032,
            dst_bytes=0,
            logged_in=0,
            count=511,
            srv_count=511,
            same_srv_rate=1.0,
            dst_host_same_src_port_rate=1.0,
        ),
    },
]


def demo_batch(limit: int = 6) -> list[dict[str, Any]]:
    """Return up to `limit` raw flow dicts for /predict."""
    return [item["flow"] for item in DEMO_FLOWS[:limit]]
