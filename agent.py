"""
Agentic planning module with observable multi-step reasoning loop.
The agent follows: Observe → Plan → Reason → Recommend, logging each step.
Each intermediate step is returned so the UI can display the chain of thought.
"""

import json
import os
import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


_AGENT_SYSTEM = """You are a number-guessing game strategy agent.
You receive game state observations and return a JSON planning step.
Always respond with valid JSON only — no prose, no markdown fences.

JSON schema:
{
  "step_name": string,
  "reasoning": string (1-2 sentences),
  "optimal_guess": integer,
  "confidence": float (0.0-1.0),
  "strategy": "binary_search" | "trisection" | "linear_scan",
  "risk": "low" | "medium" | "high"
}"""


def _observe(guess_history: list, low: int, high: int) -> dict:
    """Step 1: Deterministically compute the current valid search range."""
    cur_low, cur_high = low, high
    for entry in guess_history:
        g, outcome = entry["guess"], entry["outcome"]
        if outcome == "Too High":
            cur_high = min(cur_high, g - 1)
        elif outcome == "Too Low":
            cur_low = max(cur_low, g + 1)

    range_size = max(0, cur_high - cur_low + 1)
    return {
        "step": "observe",
        "original_range": [low, high],
        "valid_range": [cur_low, cur_high],
        "range_size": range_size,
        "guesses_made": len(guess_history),
        "elimination_rate": round(1 - range_size / max(1, high - low + 1), 3),
    }


def _plan(observation: dict) -> dict:
    """Step 2: Deterministically select a planning strategy."""
    cur_low, cur_high = observation["valid_range"]
    size = observation["range_size"]
    original_size = observation["original_range"][1] - observation["original_range"][0] + 1

    if size <= 0:
        strategy = "won"
    elif original_size > 200:
        strategy = "trisection"
    else:
        strategy = "binary_search"

    if strategy == "trisection":
        optimal = cur_low + (cur_high - cur_low) // 3
    else:
        optimal = (cur_low + cur_high) // 2

    import math
    steps_remaining = math.ceil(math.log2(max(1, size))) if strategy == "binary_search" else math.ceil(math.log(max(1, size), 3))

    return {
        "step": "plan",
        "strategy": strategy,
        "optimal_next_guess": optimal,
        "steps_needed_to_win": steps_remaining,
        "valid_range": [cur_low, cur_high],
    }


def _reason(observation: dict, plan: dict, guess_history: list) -> dict:
    """Step 3: LLM reasoning call — produces structured JSON with confidence and risk."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        size = observation["range_size"]
        return {
            "step": "reason",
            "step_name": "Deterministic fallback",
            "reasoning": f"Binary search on remaining {size} values.",
            "optimal_guess": plan["optimal_next_guess"],
            "confidence": round(min(1.0, 2.0 / max(1, size)), 3),
            "strategy": plan["strategy"],
            "risk": "low" if size < 10 else ("medium" if size < 50 else "high"),
        }

    messages = [
        {
            "role": "user",
            "content": (
                f"Game state:\n{json.dumps(observation, indent=2)}\n\n"
                f"Proposed plan:\n{json.dumps(plan, indent=2)}\n\n"
                f"Guess history: {json.dumps(guess_history)}\n\n"
                "Evaluate this plan and return your reasoning as JSON."
            ),
        }
    ]

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            system=[
                {
                    "type": "text",
                    "text": _AGENT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
        result = json.loads(response.content[0].text)
        result["step"] = "reason"
        return result
    except (json.JSONDecodeError, Exception) as e:
        size = observation["range_size"]
        return {
            "step": "reason",
            "step_name": "Fallback plan",
            "reasoning": f"LLM unavailable ({e}). Applying optimal binary search.",
            "optimal_guess": plan["optimal_next_guess"],
            "confidence": round(min(1.0, 2.0 / max(1, size)), 3),
            "strategy": plan["strategy"],
            "risk": "low",
        }


def run_agent(guess_history: list, low: int, high: int) -> dict:
    """
    Full agentic loop: Observe → Plan → Reason.
    Returns all intermediate steps for transparent display in the UI.
    """
    step1 = _observe(guess_history, low, high)
    step2 = _plan(step1)
    step3 = _reason(step1, step2, guess_history)

    return {
        "steps": [step1, step2, step3],
        "final_recommendation": {
            "optimal_guess": step3.get("optimal_guess", step2["optimal_next_guess"]),
            "strategy": step3.get("strategy", step2["strategy"]),
            "confidence": step3.get("confidence", 0.5),
            "risk": step3.get("risk", "medium"),
            "reasoning": step3.get("reasoning", ""),
            "valid_range": step1["valid_range"],
        },
    }
