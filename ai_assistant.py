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
import anthropic
from rag_retriever import retrieve_relevant_docs, format_context_for_llm, get_query_tags_for_state
from guardrails import log_ai_request, log_error

# Python 3.12+ type alias syntax
type GuessEntry = dict[str, int | str]
type GuessHistory = list[GuessEntry]
type ChatMessage = dict[str, str]

_client: anthropic.Anthropic | None = None

# ── Few-shot mode definitions (Fine-Tuning / Specialization feature) ──────────
# Each mode has a unique system prompt + 2 few-shot examples.
# The examples constrain tone/style so output measurably differs from baseline.
_MODES: dict[str, dict] = {
    "coach": {
        "label": "Coach Mode",
        "system": (
            "You are an enthusiastic strategy coach for Game Glitch Investigator. "
            "Use encouraging language, sports or game analogies, and celebrate progress. "
            "Keep hints to 1-2 sentences. Never reveal the secret number."
        ),
        "examples": [
            {
                "role": "user",
                "content": "Range: 1-100. No guesses yet.",
            },
            {
                "role": "assistant",
                "content": (
                    "Start strong like a chess grandmaster — guess 50, right in the "
                    "heart of the range! It cuts the field in half and puts you in total control."
                ),
            },
            {
                "role": "user",
                "content": "Range: 1-100. Guess 1: 50 (Too Low), Guess 2: 75 (Too High). 6 left.",
            },
            {
                "role": "assistant",
                "content": (
                    "Brilliant — you've already eliminated 74% of the range! "
                    "Aim for 62, right in the sweet spot between 51 and 74. You've got this!"
                ),
            },
        ],
    },
    "analyst": {
        "label": "Analyst Mode",
        "system": (
            "You are a mathematical game analyst for Game Glitch Investigator. "
            "Give precise, data-driven advice using exact numbers and search theory. "
            "Format: state the optimal guess and the concise mathematical reasoning. "
            "1-2 sentences only. Never reveal the secret number."
        ),
        "examples": [
            {
                "role": "user",
                "content": "Range: 1-100. No guesses yet.",
            },
            {
                "role": "assistant",
                "content": (
                    "Optimal first guess: 50 (midpoint of [1,100]). "
                    "Binary search on n=100 converges in ceil(log2(100))=7 steps — "
                    "one spare attempt on Normal difficulty."
                ),
            },
            {
                "role": "user",
                "content": "Range: 1-100. Guess 1: 50 (Too Low), Guess 2: 75 (Too High). 6 left.",
            },
            {
                "role": "assistant",
                "content": (
                    "Valid range: [51,74], size=24. Optimal next: 62 (midpoint). "
                    "Remaining depth: ceil(log2(24))=5 steps — within budget. "
                    "Win probability: ~97%."
                ),
            },
        ],
    },
}

_ANALYSIS_SYSTEM = """You are a game performance analyst for Game Glitch Investigator.
Review the player's guess history and give a brief, encouraging post-game analysis.
Mention whether their strategy was efficient (binary search = optimal) and one improvement tip.
Keep your response to 2-3 sentences."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def _build_few_shot_messages(user_message: str, mode: str) -> list[ChatMessage]:
    """Prepend few-shot examples for the given mode, then append the real user message."""
    mode_cfg = _MODES.get(mode, _MODES["coach"])
    return [*mode_cfg["examples"], {"role": "user", "content": user_message}]


def list_modes() -> list[str]:
    """Return available mode keys."""
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
    """
    Generate a RAG-augmented, few-shot-specialized strategic hint.

    Pipeline:
      1. RAG: retrieve relevant strategy docs from two sources.
      2. Specialize: prepend few-shot examples matching the selected mode.
      3. LLM: generate response grounded in retrieved docs + constrained by examples.
    """
    start = time.time()
    try:
        # ── Step 1: RAG retrieval ─────────────────────────────────────────────
        query_tags = get_query_tags_for_state(guess_history, difficulty)
        retrieved_docs = retrieve_relevant_docs(query_tags, top_k=2)
        rag_context = format_context_for_llm(retrieved_docs)

        history_str = (
            ", ".join(
                f"Guess {i + 1}: {e['guess']} ({e['outcome']})"
                for i, e in enumerate(guess_history)
            )
            if guess_history
            else "No guesses yet."
        )

        # ── Step 2: Build specialized message list ────────────────────────────
        user_message = (
            f"Retrieved context (use this to inform your hint):\n{rag_context}\n\n"
            f"Current game state:\n"
            f"- Range: {low} to {high}\n"
            f"- Attempts left: {attempts_left}\n"
            f"- Guess history: {history_str}\n\n"
            "Give a concise strategic hint grounded in the retrieved context above."
        )
        messages = _build_few_shot_messages(user_message, mode)
        mode_cfg = _MODES.get(mode, _MODES["coach"])

        # ── Step 3: LLM call with cached system + specialized messages ────────
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": mode_cfg["system"],
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )

        latency = (time.time() - start) * 1000
        hint = response.content[0].text
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
    """Post-game analysis using RAG context about optimal strategy."""
    start = time.time()
    try:
        retrieved_docs = retrieve_relevant_docs(
            ["strategy", "binary_search", "scoring"], top_k=2
        )
        rag_context = format_context_for_llm(retrieved_docs)

        history_str = "\n".join(
            f"  Attempt {i + 1}: guessed {e['guess']} -> {e['outcome']}"
            for i, e in enumerate(guess_history)
        )

        user_message = (
            f"Strategy reference:\n{rag_context}\n\n"
            f"Game summary:\n"
            f"- Range: {low} to {high} | Secret: {secret}\n"
            f"- Result: {'Won' if won else 'Lost'} in {len(guess_history)} guesses\n"
            f"- Guess history:\n{history_str}\n\n"
            "Analyze the player's strategy efficiency and give one improvement tip."
        )

        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=[
                {
                    "type": "text",
                    "text": _ANALYSIS_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        latency = (time.time() - start) * 1000
        analysis = response.content[0].text
        log_ai_request("analysis", latency, True)
        return analysis

    except Exception as e:
        latency = (time.time() - start) * 1000
        log_error("analyze_game_performance", e)
        log_ai_request("analysis", latency, False, str(e))
        raise
