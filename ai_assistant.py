"""
AI assistant module — LLM hints with RAG + few-shot specialization.

Two AI modes (Coach / Analyst) demonstrate specialized model behavior:
  - Coach: encouraging language, sports analogies, celebrates progress
  - Analyst: precise, mathematical, uses exact numbers and probabilities

Retrieved RAG context is always injected into prompts so the AI's
answers are grounded in retrieved documents, not just parametric memory.
"""

import os
import time
from google import genai
from google.genai import types
from rag_retriever import retrieve_relevant_docs, format_context_for_llm, get_query_tags_for_state
from guardrails import log_ai_request, log_error

type GuessEntry = dict[str, int | str]
type GuessHistory = list[GuessEntry]

_client: genai.Client | None = None

_MODES: dict[str, dict] = {
    "coach": {
        "label": "Coach Mode",
        "system": "You are a strategy coach. Give 1 encouraging hint using a game analogy. Never reveal the secret.",
        "examples": [
            types.Content(role="user", parts=[types.Part(text="Range: 1-100. No guesses yet.")]),
            types.Content(
                role="model",
                parts=[types.Part(text="Guess 50 — split the field in half like a chess grandmaster!")],
            ),
        ],
    },
    "analyst": {
        "label": "Analyst Mode",
        "system": "You are a math analyst. Give 1 precise hint with the optimal guess and brief reasoning. Never reveal the secret.",
        "examples": [
            types.Content(role="user", parts=[types.Part(text="Range: 1-100. No guesses yet.")]),
            types.Content(
                role="model",
                parts=[types.Part(text="Optimal: 50 (midpoint). Binary search converges in ceil(log2(100))=7 steps.")],
            ),
        ],
    },
}

_ANALYSIS_SYSTEM = """You are a game performance analyst for Game Glitch Investigator.
Review the player's guess history and give a brief, encouraging post-game analysis.
Mention whether their strategy was efficient (binary search = optimal) and one improvement tip.
Keep your response to 2-3 sentences."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GOOGLE_GEMINI_API_KEY"))
    return _client


def list_modes() -> list[str]:
    return list(_MODES.keys())


def get_mode_label(mode: str) -> str:
    return _MODES.get(mode, _MODES["coach"])["label"]


def get_ai_hint(
    guess_history: GuessHistory,
    low: int,
    high: int,
    attempts_left: int,
    difficulty: str = "Normal",
    mode: str = "coach",
) -> str:
    start = time.time()
    try:
        query_tags = get_query_tags_for_state(guess_history, difficulty)
        retrieved_docs = retrieve_relevant_docs(query_tags, top_k=1)
        rag_context = format_context_for_llm(retrieved_docs)

        history_str = (
            ", ".join(f"{e['guess']}({e['outcome']})" for e in guess_history)
            if guess_history else "none"
        )

        user_message = (
            f"Tip: {rag_context}\n"
            f"Range:{low}-{high} | Left:{attempts_left} | History:{history_str}"
        )

        mode_cfg = _MODES.get(mode, _MODES["coach"])
        chat = _get_client().chats.create(
            model="gemini-2.0-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=mode_cfg["system"],
                max_output_tokens=80,
            ),
            history=mode_cfg["examples"],
        )
        response = chat.send_message(user_message)

        latency = (time.time() - start) * 1000
        hint = response.text
        log_ai_request("hint", latency, True, f"rag_docs={len(retrieved_docs)} mode={mode}")
        return hint

    except Exception as e:
        latency = (time.time() - start) * 1000
        log_error("get_ai_hint", e)
        log_ai_request("hint", latency, False, str(e))
        raise


def analyze_game_performance(
    guess_history: GuessHistory,
    secret: int,
    won: bool,
    low: int,
    high: int,
) -> str:
    start = time.time()
    try:
        retrieved_docs = retrieve_relevant_docs(
            ["strategy", "binary_search", "scoring"], top_k=1
        )
        rag_context = format_context_for_llm(retrieved_docs)

        history_str = ", ".join(
            f"{e['guess']}({e['outcome']})" for e in guess_history
        )

        user_message = (
            f"Tip: {rag_context}\n"
            f"Range:{low}-{high} Secret:{secret} "
            f"Result:{'Won' if won else 'Lost'} in {len(guess_history)} guesses. "
            f"History:{history_str}"
        )

        response = _get_client().models.generate_content(
            model="gemini-2.0-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=_ANALYSIS_SYSTEM,
                max_output_tokens=120,
            ),
            contents=user_message,
        )

        latency = (time.time() - start) * 1000
        analysis = response.text
        log_ai_request("analysis", latency, True)
        return analysis

    except Exception as e:
        latency = (time.time() - start) * 1000
        log_error("analyze_game_performance", e)
        log_ai_request("analysis", latency, False, str(e))
        raise
