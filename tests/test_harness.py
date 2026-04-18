"""
Evaluation test harness — runs predefined test cases and prints a summary.
Usage: python tests/test_harness.py
Runs without a live API key (uses offline stubs for AI features).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logic_utils import check_guess, update_score
from guardrails import validate_guess_input, sanitize_ai_response, rate_limit_check
from rag_retriever import retrieve_relevant_docs, get_query_tags_for_state
from agent import _observe, _plan
from evaluation import score_hint_relevance


def run_test(name: str, fn) -> dict:
    try:
        fn()
        return {"name": name, "status": "PASS", "error": None}
    except AssertionError as e:
        return {"name": name, "status": "FAIL", "error": str(e) or "AssertionError"}
    except Exception as e:
        return {"name": name, "status": "ERROR", "error": str(e)}


# ── Test cases ────────────────────────────────────────────────────────────────

def tc_binary_search_convergence():
    """Simulate binary search winning on a 1-100 range in ≤7 guesses."""
    secret = 73
    low, high = 1, 100
    history = []
    for _ in range(1, 8):
        guess = (low + high) // 2
        outcome, _ = check_guess(guess, secret)
        history.append({"guess": guess, "outcome": outcome})
        if outcome == "Win":
            return
        if outcome == "Too High":
            high = guess - 1
        else:
            low = guess + 1
    assert False, "Binary search should win in ≤7 guesses on 1-100"


def tc_guardrail_blocks_injection():
    ok, _ = validate_guess_input("<script>alert(1)</script>", 1, 100)
    assert not ok, "Script injection should be blocked"


def tc_guardrail_valid_boundary():
    ok, _ = validate_guess_input("1", 1, 100)
    assert ok, "Boundary value 1 should be valid"
    ok2, _ = validate_guess_input("100", 1, 100)
    assert ok2, "Boundary value 100 should be valid"


def tc_score_does_not_go_negative():
    score = update_score(2, "Too High", 1)
    assert score == 0, f"Score floored to 0, got {score}"


def tc_rag_returns_results():
    tags = get_query_tags_for_state([], "Normal")
    docs = retrieve_relevant_docs(tags, top_k=2)
    assert len(docs) >= 1, "RAG should return at least 1 document for strategy query"


def tc_rag_hard_mode_retrieves_trisection():
    tags = get_query_tags_for_state([], "Hard")
    docs = retrieve_relevant_docs(tags, top_k=3)
    topics = [d["topic"].lower() for d in docs]
    assert any("trisect" in t or "hard" in t for t in topics), \
        f"Hard mode RAG should retrieve trisection tip. Got: {topics}"


def tc_agent_observe_narrows_range():
    history = [
        {"guess": 50, "outcome": "Too Low"},
        {"guess": 75, "outcome": "Too High"},
    ]
    obs = _observe(history, 1, 100)
    lo, hi = obs["valid_range"]
    assert lo == 51 and hi == 74, f"Expected (51,74), got ({lo},{hi})"


def tc_agent_plan_optimal_guess():
    obs = {"valid_range": [51, 74], "range_size": 24, "original_range": [1, 100], "guesses_made": 2}
    plan = _plan(obs)
    assert plan["optimal_next_guess"] == 62, f"Expected 62, got {plan['optimal_next_guess']}"


def tc_hint_relevance_scorer():
    hint = "Use binary search: guess the midpoint of your remaining range."
    metrics = score_hint_relevance(hint, 1, 100, [])
    assert metrics["mentions_strategy"], "Hint mentioning binary search should score mentions_strategy=True"
    assert metrics["overall_score"] >= 0.5


def tc_sanitize_strips_injection():
    dirty = "great hint! <script>steal()</script>"
    result = sanitize_ai_response(dirty)
    assert result == "Response filtered for safety."


def tc_rate_limit_enforced():
    ok_before, _ = rate_limit_check(14, max_per_game=15)
    ok_at, _ = rate_limit_check(15, max_per_game=15)
    assert ok_before and not ok_at


# ── Runner ────────────────────────────────────────────────────────────────────

TESTS = [
    ("Binary search wins in ≤7 guesses", tc_binary_search_convergence),
    ("Guardrail: blocks script injection", tc_guardrail_blocks_injection),
    ("Guardrail: accepts valid boundary values", tc_guardrail_valid_boundary),
    ("Score: does not go negative", tc_score_does_not_go_negative),
    ("RAG: returns results for strategy query", tc_rag_returns_results),
    ("RAG: Hard mode retrieves trisection tip", tc_rag_hard_mode_retrieves_trisection),
    ("Agent: observe step narrows range correctly", tc_agent_observe_narrows_range),
    ("Agent: plan step picks optimal midpoint", tc_agent_plan_optimal_guess),
    ("Evaluation: hint relevance scorer works", tc_hint_relevance_scorer),
    ("Sanitizer: strips injection patterns", tc_sanitize_strips_injection),
    ("Rate limiter: enforces request cap", tc_rate_limit_enforced),
]


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("\n" + "=" * 60)
    print("  GAME GLITCH INVESTIGATOR -- AI SYSTEM TEST HARNESS")
    print("=" * 60)

    results = [run_test(name, fn) for name, fn in TESTS]

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    for r in results:
        symbol = {"PASS": "[PASS]", "FAIL": "[FAIL]", "ERROR": "[ERROR]"}.get(r["status"], "?")
        line = f"  {symbol} {r['name']}"
        if r["error"]:
            line += f"\n       -> {r['error']}"
        print(line)

    print("\n" + "-" * 60)
    print(f"  Results: {passed} passed / {failed} failed / {errors} errors")
    print(f"  Total: {len(TESTS)} tests")

    if failed + errors == 0:
        print("\n  All tests passed.")
    else:
        print(f"\n  {failed + errors} test(s) need attention.")
    print("=" * 60 + "\n")

    return 0 if (failed + errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
