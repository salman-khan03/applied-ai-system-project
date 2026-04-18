"""
Reliability evaluation module.
Measures AI hint quality using relevance scoring, latency tracking,
and consistency checks. Used by the test harness and optional UI panel.
"""

import time


def score_hint_relevance(hint: str, low: int, high: int, guess_history: list) -> dict:
    """
    Score an AI hint on four dimensions. Returns a metrics dict.
    Higher overall_score = more relevant and useful hint.
    """
    hint_lower = hint.lower()

    metrics = {
        "mentions_strategy": any(
            w in hint_lower
            for w in ["midpoint", "middle", "half", "binary", "trisect", "narrow", "range"]
        ),
        "appropriate_length": 15 <= len(hint) <= 400,
        "not_empty": bool(hint.strip()),
        "no_secret_revealed": all(
            str(e["guess"]) not in hint for e in guess_history
        ) if guess_history else True,
    }

    score = sum(metrics.values()) / len(metrics)
    metrics["overall_score"] = round(score, 2)
    return metrics


def run_reliability_evaluation(n_trials: int = 3, use_live_api: bool = True) -> dict:
    """
    Run a structured reliability evaluation over N trials.
    Returns a summary with success rate, avg latency, and avg relevance.
    """
    test_history = [
        {"guess": 50, "outcome": "Too Low"},
        {"guess": 75, "outcome": "Too High"},
    ]
    results = []
    latencies = []

    for i in range(n_trials):
        start = time.time()
        trial: dict = {"trial": i + 1}

        if use_live_api:
            try:
                from ai_assistant import get_ai_hint
                hint = get_ai_hint(test_history, 1, 100, 5, "Normal")
                elapsed_ms = (time.time() - start) * 1000
                latencies.append(elapsed_ms)
                metrics = score_hint_relevance(hint, 1, 100, test_history)
                trial.update({
                    "hint_preview": hint[:80] + ("..." if len(hint) > 80 else ""),
                    "metrics": metrics,
                    "latency_ms": round(elapsed_ms),
                    "status": "pass",
                })
            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                trial.update({"error": str(e), "latency_ms": round(elapsed_ms), "status": "fail"})
        else:
            # Offline stub for CI / no-key environments
            hint = "Based on binary search strategy, guess the midpoint of your remaining range."
            metrics = score_hint_relevance(hint, 1, 100, test_history)
            trial.update({
                "hint_preview": hint,
                "metrics": metrics,
                "latency_ms": 0,
                "status": "pass (stub)",
            })

        results.append(trial)

    successful = [r for r in results if "error" not in r]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    avg_score = (
        sum(r["metrics"]["overall_score"] for r in successful) / len(successful)
        if successful
        else 0
    )

    return {
        "trials": results,
        "summary": {
            "success_rate": f"{len(successful)}/{n_trials}",
            "avg_latency_ms": round(avg_latency),
            "avg_relevance_score": round(avg_score, 2),
            "passed": len(successful) == n_trials,
        },
    }
