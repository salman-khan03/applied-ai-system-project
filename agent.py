"""
Agentic planning module with observable multi-step reasoning loop.
The agent follows: Observe → Plan → Reason → Recommend, logging each step.
Each intermediate step is returned so the UI can display the chain of thought.
"""

import json
import math
import os
import re
from google import genai
from google.genai import types

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GOOGLE_GEMINI_API_KEY"))
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

    if strategy == "binary_search":
        steps_remaining = math.ceil(math.log2(max(1, size)))
    else:
        steps_remaining = math.ceil(math.log(max(1, size), 3))

    return {
        "step": "plan",
        "strategy": strategy,
        "optimal_next_guess": optimal,
        "steps_needed_to_win": steps_remaining,
        "valid_range": [cur_low, cur_high],
    }


def _reason(observation: dict, plan: dict, guess_history: list) -> dict:
    """Step 3: LLM reasoning call — produces structured JSON with confidence and risk."""
    if not os.environ.get("GOOGLE_GEMINI_API_KEY"):
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

    size = observation["range_size"]
    vr = observation["valid_range"]
    prompt = (
        f"range:[{vr[0]},{vr[1]}] size:{size} "
        f"strategy:{plan['strategy']} guess:{plan['optimal_next_guess']} "
        f"history:{[(e['guess'], e['outcome']) for e in guess_history]}"
    )

    try:
        response = _get_client().models.generate_content(
            model="gemini-2.0-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=_AGENT_SYSTEM,
                max_output_tokens=120,
            ),
            contents=prompt,
        )
        raw = re.sub(r"^```(?:json)?\s*", "", response.text.strip())
        raw = re.sub(r"\s*```$", "", raw).strip()
        result = json.loads(raw)
        result["step"] = "reason"
        return result
    except Exception as e:
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
