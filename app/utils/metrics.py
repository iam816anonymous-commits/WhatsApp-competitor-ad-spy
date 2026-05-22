import time
import logging
from typing import Dict, Any

logger = logging.getLogger("AdSpyAgent.Metrics")

class MetricsEngine:
    _metrics = {
        "latencies": [],
        "failures": 0,
        "total_tasks": 0,
        "prediction_drift": 0.05 # placeholder
    }

    @classmethod
    def record_latency(cls, duration_ms: float):
        cls._metrics["latencies"].append(duration_ms)
        if len(cls._metrics["latencies"]) > 1000:
            cls._metrics["latencies"].pop(0)

    @classmethod
    def record_failure(cls):
        cls._metrics["failures"] += 1

    @classmethod
    def record_task(cls):
        cls._metrics["total_tasks"] += 1

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        lats = cls._metrics["latencies"]
        p95 = sorted(lats)[int(len(lats)*0.95)] if lats else 0
        p99 = sorted(lats)[int(len(lats)*0.99)] if lats else 0

        failure_rate = (cls._metrics["failures"] / cls._metrics["total_tasks"] * 100) if cls._metrics["total_tasks"] > 0 else 0

        return {
            "p95_ms": p95,
            "p99_ms": p99,
            "failure_rate_pct": failure_rate,
            "total_tasks": cls._metrics["total_tasks"],
            "prediction_drift": cls._metrics["prediction_drift"]
        }
