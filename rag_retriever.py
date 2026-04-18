"""
RAG retrieval system with two data sources:
  1. In-memory structured knowledge base (bug patterns + strategies)
  2. Text file: assets/game_strategy_guide.txt (detailed strategy guide)

Retrieved context is passed directly into the LLM prompt so the AI's
response is grounded in the retrieved documents.
"""

import os
from pathlib import Path

# ── Source 1: Structured knowledge base ──────────────────────────────────────
KNOWLEDGE_BASE = [
    {
        "id": "binary_search",
        "topic": "Binary Search Strategy",
        "content": "Always guess the midpoint of your remaining valid range. For range [L,H], guess (L+H)//2. This eliminates half the search space per turn and is optimal for Easy/Normal difficulty.",
        "tags": ["strategy", "optimal", "binary_search", "efficient"],
    },
    {
        "id": "range_update",
        "topic": "Range Narrowing",
        "content": "After 'Too High': set new_high = guess - 1. After 'Too Low': set new_low = guess + 1. Never guess outside your current valid range.",
        "tags": ["strategy", "range", "narrowing", "update"],
    },
    {
        "id": "hard_mode_trisection",
        "topic": "Hard Mode: Trisection",
        "content": "Hard mode has 500 numbers but only 5 attempts. Binary search needs 9 steps — not enough. Use trisection: split range into thirds each turn. This solves Hard in at most 6 steps.",
        "tags": ["strategy", "hard", "trisection", "difficulty"],
    },
    {
        "id": "state_reset_bug",
        "topic": "Streamlit State Reset Bug",
        "content": "Bug: secret number changes every click. Cause: Streamlit reruns the full script on each interaction. Fix: use st.session_state to persist variables. Example: if 'secret' not in st.session_state: st.session_state.secret = random.randint(low, high)",
        "tags": ["bug", "streamlit", "state", "session", "debugging"],
    },
    {
        "id": "hint_inversion_bug",
        "topic": "Inverted Hint Bug",
        "content": "Bug: 'Go Higher' when guess is too high (and vice versa). Cause: comparison operators flipped. Fix: if guess > secret → 'Too High, Go LOWER'; if guess < secret → 'Too Low, Go HIGHER'.",
        "tags": ["bug", "logic", "hints", "comparison", "debugging"],
    },
    {
        "id": "type_mismatch_bug",
        "topic": "Type Mismatch Bug",
        "content": "Bug: string input compared to integer secret causes wrong results. Fix: always parse input with int(raw) before comparing. Validate that input is numeric first.",
        "tags": ["bug", "types", "parsing", "validation", "debugging"],
    },
    {
        "id": "scoring_strategy",
        "content": "Scoring: Win on attempt 1 = +90 pts, attempt 5 = +50 pts. Each wrong guess = -5 pts. Minimize guesses to maximize score. Binary search minimizes guesses.",
        "topic": "Scoring Optimization",
        "tags": ["strategy", "scoring", "optimization", "points"],
    },
    {
        "id": "early_game",
        "topic": "Early Game (No History)",
        "content": "With no guess history, start with the midpoint of the full range. For Easy(1-20): guess 10. For Normal(1-100): guess 50. For Hard(1-500): guess 167 (trisection first point).",
        "tags": ["strategy", "early_game", "first_guess", "start"],
    },
]

_GUIDE_PATH = Path(__file__).parent / "assets" / "game_strategy_guide.txt"


def _load_guide_chunks() -> list[dict]:
    """Load and chunk the strategy guide text file into retrievable segments."""
    if not _GUIDE_PATH.exists():
        return []

    text = _GUIDE_PATH.read_text(encoding="utf-8")
    chunks = []
    current_section = []
    current_title = "General"

    for line in text.splitlines():
        if line.startswith("---") or (line.isupper() and len(line) > 3 and not line.startswith(" ")):
            if current_section:
                chunks.append({
                    "id": f"guide_{current_title.lower().replace(' ', '_')}",
                    "topic": current_title,
                    "content": " ".join(current_section).strip(),
                    "tags": ["guide", "strategy"],
                    "source": "game_strategy_guide.txt",
                })
            current_title = line.strip("-").strip()
            current_section = []
        elif line.strip():
            current_section.append(line.strip())

    if current_section:
        chunks.append({
            "id": f"guide_{current_title.lower().replace(' ', '_')}",
            "topic": current_title,
            "content": " ".join(current_section).strip(),
            "tags": ["guide", "strategy"],
            "source": "game_strategy_guide.txt",
        })
    return chunks


def retrieve_relevant_docs(query_tags: list[str], top_k: int = 3) -> list[dict]:
    """
    Retrieve top-k most relevant documents from both sources using tag overlap.
    This is the core RAG retrieval step — results are passed to the LLM prompt.
    """
    all_docs = KNOWLEDGE_BASE + _load_guide_chunks()
    scored = []
    for doc in all_docs:
        overlap = len(set(query_tags) & set(doc.get("tags", [])))
        if overlap > 0:
            scored.append((overlap, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def format_context_for_llm(docs: list[dict]) -> str:
    """Format retrieved documents as context text for injection into LLM prompts."""
    if not docs:
        return "No additional context available."
    lines = []
    for i, doc in enumerate(docs, 1):
        src = doc.get("source", "knowledge_base")
        lines.append(f"[Source {i} — {doc['topic']} ({src})]")
        lines.append(doc["content"])
        lines.append("")
    return "\n".join(lines)


def format_tips_for_display(docs: list[dict]) -> str:
    """Format retrieved docs for Streamlit sidebar display."""
    if not docs:
        return "No tips found for selected tags."
    lines = []
    for doc in docs:
        lines.append(f"**{doc['topic']}**")
        lines.append(doc["content"])
        lines.append("")
    return "\n".join(lines)


def get_query_tags_for_state(guess_history: list, difficulty: str) -> list[str]:
    """Determine what tags to query based on current game state."""
    tags = ["strategy"]
    if not guess_history:
        tags += ["early_game", "first_guess"]
    else:
        tags += ["range", "narrowing"]
    if difficulty == "Hard":
        tags += ["hard", "trisection"]
    if len(guess_history) >= 4:
        tags += ["scoring", "optimization"]
    return tags
