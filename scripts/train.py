"""Train supervised + anomaly IDS models and write artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netguard.train import run_training


def main() -> int:
    result = run_training()
    metrics = result.metrics

    print("[ok] training complete")
    print(f"  artifacts → {result.model_dir}")

    if "supervised" in metrics:
        s = metrics["supervised"]
        print(
            "  supervised  "
            f"acc={s['accuracy']:.4f}  "
            f"f1_macro={s['f1_macro']:.4f}  "
            f"f1_weighted={s['f1_weighted']:.4f}  "
            f"({s['algorithm']})"
        )

    if "anomaly" in metrics:
        a = metrics["anomaly"]
        roc = a.get("roc_auc")
        roc_str = f"{roc:.4f}" if isinstance(roc, float) else "n/a"
        print(
            "  anomaly     "
            f"f1={a['f1']:.4f}  "
            f"precision={a['precision']:.4f}  "
            f"recall={a['recall']:.4f}  "
            f"roc_auc={roc_str}  "
            f"({a['algorithm']})"
        )

    metrics_path = result.model_dir / "metrics.json"
    print(f"  metrics     → {metrics_path}")
    # Echo a short JSON summary for copy/paste into notes
    summary = {
        k: metrics[k]
        for k in ("supervised", "anomaly")
        if k in metrics
    }
    print(json.dumps(summary, indent=2)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
