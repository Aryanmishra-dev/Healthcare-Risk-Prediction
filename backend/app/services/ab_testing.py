"""
A/B testing framework for model comparison.

Routes a configurable percentage of traffic to a challenger model while the
champion model serves the remainder.  Results are logged so offline analysis
can determine whether to promote the challenger.

Usage:
    from backend.app.services.ab_testing import ab_router

    # Register a challenger for the diabetes model:
    ab_router.register("diabetes", challenger_fn=my_new_predict, traffic_pct=10)

    # Route prediction through A/B splitter:
    result, variant = ab_router.route("diabetes", **kwargs)
    # variant is "champion" or "challenger"
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    """A single A/B test experiment configuration."""

    name: str
    champion_fn: Callable[..., dict]
    challenger_fn: Callable[..., dict]
    traffic_pct: int = 10  # % of traffic routed to challenger
    results: list[dict] = field(default_factory=list)

    def record(self, variant: str, result: dict, latency_ms: float) -> None:
        self.results.append(
            {
                "variant": variant,
                "risk_percentage": result.get("risk_percentage"),
                "risk_level": result.get("risk_level"),
                "latency_ms": round(latency_ms, 2),
                "timestamp": time.time(),
            }
        )


class ABRouter:
    """Routes prediction traffic between champion and challenger models."""

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}

    def register(
        self,
        model_name: str,
        champion_fn: Callable[..., dict],
        challenger_fn: Callable[..., dict],
        traffic_pct: int = 10,
    ) -> None:
        """Register a new A/B experiment for a model."""
        if not 0 <= traffic_pct <= 100:
            raise ValueError("traffic_pct must be between 0 and 100")
        self._experiments[model_name] = Experiment(
            name=model_name,
            champion_fn=champion_fn,
            challenger_fn=challenger_fn,
            traffic_pct=traffic_pct,
        )
        logger.info(
            "A/B experiment registered: %s (challenger gets %d%% traffic)",
            model_name,
            traffic_pct,
        )

    def route(
        self, model_name: str, request_id: str = "", **kwargs: Any
    ) -> tuple[dict, str]:
        """
        Route a prediction to champion or challenger.

        Uses a deterministic hash of request_id for consistent bucketing.
        Returns (result_dict, variant_name).
        """
        exp = self._experiments.get(model_name)
        if exp is None:
            raise KeyError(f"No A/B experiment registered for '{model_name}'")

        # Deterministic bucketing based on request_id
        bucket = int(hashlib.sha256(request_id.encode()).hexdigest(), 16) % 100
        use_challenger = bucket < exp.traffic_pct

        start = time.time()
        if use_challenger:
            result = exp.challenger_fn(**kwargs)
            variant = "challenger"
        else:
            result = exp.champion_fn(**kwargs)
            variant = "champion"
        latency = (time.time() - start) * 1000

        exp.record(variant, result, latency)
        logger.info(
            "A/B routed %s → %s (bucket=%d, latency=%.1fms)",
            model_name,
            variant,
            bucket,
            latency,
        )
        return result, variant

    def get_summary(self, model_name: str) -> dict:
        """Return summary statistics for an A/B experiment."""
        exp = self._experiments.get(model_name)
        if exp is None:
            return {"error": f"No experiment for '{model_name}'"}
        champion = [r for r in exp.results if r["variant"] == "champion"]
        challenger = [r for r in exp.results if r["variant"] == "challenger"]

        def _stats(records: list[dict]) -> dict:
            if not records:
                return {"count": 0}
            latencies = [r["latency_ms"] for r in records]
            return {
                "count": len(records),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
                "avg_risk": round(
                    sum(r["risk_percentage"] for r in records) / len(records), 2
                ),
            }

        return {
            "experiment": model_name,
            "traffic_pct": exp.traffic_pct,
            "champion": _stats(champion),
            "challenger": _stats(challenger),
            "total_requests": len(exp.results),
        }

    @property
    def active_experiments(self) -> list[str]:
        return list(self._experiments.keys())


# Module-level singleton
ab_router = ABRouter()
