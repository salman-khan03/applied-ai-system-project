"""
AI assistant module — LLM-powered hints and post-game analysis.
RAG context from rag_retriever is injected into every LLM prompt so the
AI's answers are grounded in retrieved documents (not just parametric memory).
"""

import os
import time
import anthropic
from rag_retriever import retrieve_relevant_docs, format_context_for_llm, get_query_tags_for_state
from guardrails import log_ai_request, log_error

_client: anthropic.Anthropic | None = None

_HINT_SYSTEM = """You are a helpful strategy coach for a number guessing game called Game Glitch Investigator.
Use the provided context documents to give accurate, concise strategic hints.
Never reveal or calculate the exact secret number. Keep hints to 1-2 sentences.
Base your advice on the retrieved context when relevant."""

_ANALYSIS_SYSTEM = """You are a game performance analyst for Game Glitch Investigator.
Review the player's guess history and give a brief, encouraging post-game analysis.
Mention whether their strategy was efficient (binary search = optimal) and one improvement tip.
Keep your response to 2-3 sentences."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def get_ai_hint(
    guess_history: list,
    low: int,
    high: int,
    attempts_left: int,
    difficulty: str = "Normal",
) -> str:
    """
    Generate a RAG-augmented strategic hint.
    Retrieved documents are injected as context before the LLM generates a response.
    """
    start = time.time()
    try:
        # RAG retrieval step
        query_tags = get_query_tags_for_state(guess_history, difficulty)
        retrieved_docs = retrieve_relevant_docs(query_tags, top_k=2)
        rag_context = format_context_for_llm(retrieved_docs)

        history_str = (
            ", ".join(
                f"Guess {i+1}: {e['guess']} ({e['outcome']})"
                for i, e in enumerate(guess_history)
            )
            if guess_history
            else "No guesses yet."
        )

        user_message = (
            f"Retrieved context (use this to inform your hint):\n{rag_context}\n\n"
            f"Current game state:\n"
            f"- Range: {low} to {high}\n"
            f"- Attempts left: {attempts_left}\n"
            f"- Guess history: {history_str}\n\n"
            "Give a concise strategic hint grounded in the retrieved context above."
        )

        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": _HINT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        latency = (time.time() - start) * 1000
        hint = response.content[0].text
        log_ai_request("hint", latency, True, f"rag_docs={len(retrieved_docs)}")
        return hint

    except Exception as e:
        latency = (time.time() - start) * 1000
        log_error("get_ai_hint", e)
        log_ai_request("hint", latency, False, str(e))
        raise


def analyze_game_performance(
    guess_history: list,
    secret: int,
    won: bool,
    low: int,
    high: int,
) -> str:
    """Post-game analysis using RAG context about optimal strategy."""
    start = time.time()
    try:
        # Retrieve strategy context for grounded analysis
        retrieved_docs = retrieve_relevant_docs(
            ["strategy", "binary_search", "scoring"], top_k=2
        )
        rag_context = format_context_for_llm(retrieved_docs)

        history_str = "\n".join(
            f"  Attempt {i+1}: guessed {e['guess']} → {e['outcome']}"
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
