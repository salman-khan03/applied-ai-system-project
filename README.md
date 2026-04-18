# 🎮 Game Glitch Investigator — Applied AI Edition

**CodePath AI 110 | Final Project (Module 4) | April 2026**

> 🎥 **Demo Walkthrough:** [Loom video link — add after recording]

---

## Original Project

**Base project:** Game Glitch Investigator (Module 1 — Show What You Know)

The original project was a deliberately buggy Streamlit number guessing game where players had to identify and fix three AI-generated bugs: (1) a state reset bug where the secret number changed on every button click, (2) inverted "Too High / Too Low" hints, and (3) unimplemented logic functions in `logic_utils.py` that raised `NotImplementedError`. The goal was to practice reading AI-generated code critically and applying systematic debugging.

---

## What This System Does

This project extends the Game Glitch Investigator into a full **Applied AI Debugging and Strategy System**. The AI now actively helps players improve their guessing strategy using:

- **RAG-powered hints** — Claude retrieves strategy documents before answering, so hints are grounded in a curated knowledge base (not just guesswork)
- **Agentic 3-step planning** — an agent runs Observe → Plan → Reason to show its chain of thought before recommending the optimal next guess
- **Post-game AI analysis** — after each game, Claude reviews the player's guessing pattern and scores their efficiency
- **Input guardrails + logging** — all inputs are validated, all AI calls are logged with latency and status to `game.log`
- **Automated test harness** — 11 predefined tests verify correctness without needing a live API

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Player (Browser)                   │
└──────────────────────┬──────────────────────────────┘
                       │ input
┌──────────────────────▼──────────────────────────────┐
│             Streamlit UI  (app.py)                  │
│   ┌──────────────┐  ┌──────────────┐                │
│   │  Game Column │  │  AI Column   │                │
│   │  submit/     │  │  hint btn    │                │
│   │  history     │  │  agent btn   │                │
│   └──────┬───────┘  └──────┬───────┘                │
└──────────┼─────────────────┼───────────────────────-┘
           │                 │
    ┌──────▼──────┐   ┌──────▼──────────────┐
    │ Guardrails  │   │  AI Assistant        │
    │ guardrails  │   │  ai_assistant.py     │
    │  .py        │   │  (RAG + LLM calls)  │
    │ validate    │   └──────┬──────────────┘
    │ sanitize    │          │ retrieval
    │ log         │   ┌──────▼──────────────┐
    └──────┬──────┘   │  RAG Retriever      │
           │          │  rag_retriever.py   │
    ┌──────▼──────┐   │  Source 1: KB list  │
    │ Game Logic  │   │  Source 2: .txt file│
    │ logic_utils │   └──────┬──────────────┘
    │  .py        │          │ context docs
    └─────────────┘   ┌──────▼──────────────┐
                      │  Claude Haiku 4.5   │
                      │  (Anthropic API)    │
                      │  prompt caching     │
                      └──────┬──────────────┘
                             │ response
                      ┌──────▼──────────────┐
                      │  Agent Planner      │
                      │  agent.py           │
                      │  Observe→Plan→Reason│
                      └──────┬──────────────┘
                             │
                      ┌──────▼──────────────┐
                      │  Evaluation         │
                      │  evaluation.py      │
                      │  tests/             │
                      └─────────────────────┘
```

**Data flow:** Player input → Guardrails validate → Game logic processes → RAG retrieves relevant docs → LLM generates response grounded in docs → Agent runs 3-step reasoning loop → Sanitized output displayed → All events logged.

See `assets/architecture.md` for the Mermaid diagram source.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) (free tier works)

### 1. Clone the repo
```bash
git clone https://github.com/salman-khan03/applied-ai-system-project.git
cd applied-ai-system-project
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
# Mac / Linux
export ANTHROPIC_API_KEY=sk-ant-...

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-...

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

> **Note:** The app runs without an API key — AI features are gracefully disabled and a warning is shown. All game logic and guardrails still work.

### 4. Run the app
```bash
streamlit run app.py
```

### 5. Run the test harness (no API key needed)
```bash
python tests/test_harness.py
```

### 6. Run unit tests
```bash
pytest tests/ -v
```

---

## Sample Interactions

### Example 1 — RAG-Powered AI Hint (Early Game)

**Player:** Opens the game (Easy mode, range 1–20). Clicks "💡 Get AI Hint (RAG)" before guessing.

**System behavior:** RAG retrieves the "Early Game" and "Binary Search Strategy" documents. These are injected into the Claude prompt.

**AI Output:**
> "Start with 10 — the midpoint of 1–20. Binary search guarantees you'll win Easy mode in at most 5 guesses, leaving you one spare attempt."

---

### Example 2 — Agentic Planner After Two Guesses

**Player:** Guesses 50 (Too Low), then 75 (Too High) on Normal mode.

**Player:** Clicks "📊 Run Agent (3-Step Plan)".

**Agent Steps Displayed:**
```
Step 1 — Observe:
  valid_range: [51, 74], range_size: 24, elimination_rate: 0.76

Step 2 — Plan:
  strategy: binary_search, optimal_next_guess: 62, steps_needed_to_win: 5

Step 3 — Reason (LLM):
  "After eliminating 76% of the range, binary search on [51,74] recommends
   guessing 62. With 6 attempts remaining, you have a high probability of
   winning — confidence: 0.83, risk: low."
```

**UI shows:** Valid Range: 51–74 | Optimal Next Guess: 62 | Confidence: 83% | Strategy: binary_search

---

### Example 3 — Guardrail Blocking Invalid Input

**Player:** Types `<script>alert(1)</script>` in the guess field.

**System:** `validate_guess_input()` regex check blocks the input before it reaches game logic.

**UI shows:** ❌ "Invalid input. Please enter a whole number."

**game.log entry:**
```
2026-04-17 20:30:15 | INFO | GUESS | attempt=1 guess=... (blocked before logging)
```

---

### Example 4 — Post-Game AI Analysis

**Player:** Loses on Hard mode after 5 guesses (guesses: 250, 125, 375, 312, 343 — linear probing, not optimal).

**AI Output:**
> "Your guesses followed a back-and-forth pattern rather than consistent binary search, which used all 5 attempts without converging. For Hard mode, trisection (splitting the 500-number range into thirds: 167, then 334) would have been more efficient. Next time, always guess the midpoint of your remaining valid range!"

---

## Design Decisions

| Decision | Reasoning | Trade-off |
|----------|-----------|-----------|
| Claude Haiku over Sonnet | Haiku is 10× cheaper and fast enough for 1-2 sentence hints | Less nuanced reasoning for complex cases |
| Prompt caching on system prompts | Reduces latency by ~30% on repeated calls | Small upfront cost for first call |
| Local knowledge base over vector DB | No external dependencies, runs offline, fast retrieval | Less semantic search; relies on tag matching |
| Two RAG sources (KB + text file) | Satisfies stretch feature; text file is editable without code changes | Chunking is simple line-based, not semantic |
| Deterministic Observe + Plan steps | Reliable, testable, no LLM needed for math | LLM only used for the reasoning step (cost efficiency) |
| Graceful degradation without API key | Project runs in any environment | Users must set key to see AI features |

---

## Testing Summary

**Unit tests (pytest):** 24 tests across `test_game_logic.py` and `test_guardrails.py`
- All 24 pass without API key
- Covers: check_guess correctness, hint inversion regression, score floor, parse edge cases, guardrail boundary values, injection blocking, rate limiting

**Test harness (`test_harness.py`):** 11 predefined scenario tests
- All 11 pass without API key
- Covers: binary search convergence, RAG retrieval accuracy, agent range narrowing math, sanitizer filtering, rate limiter enforcement

**Reliability evaluation (`evaluation.py`):** Measures live AI hint quality
- Run: `python -c "from evaluation import run_reliability_evaluation; import json; print(json.dumps(run_reliability_evaluation(3), indent=2))"`
- Measures: success rate, avg latency (ms), avg relevance score (0–1)
- In testing: 3/3 trials passed, avg latency ~800ms, avg relevance 0.75

**What worked:** Guardrails caught all injection attempts. RAG correctly retrieves trisection tips for Hard mode. Agent math is exact.

**What didn't:** The LLM occasionally returns a near-optimal guess that effectively spoils the game. The `no_secret_revealed` check in the evaluator only catches exact matches, not near-misses.

---

## Reflection

**What this taught me about AI:** RAG is not just "add context to prompt" — the retrieval step determines whether the AI gives useful or generic advice. When I switched from raw string matching to tag-based retrieval, hint quality improved noticeably. Agentic systems are most reliable when the deterministic steps (observe, plan) are separated from the probabilistic step (reason), so the system doesn't fail if the LLM produces invalid JSON.

**Limitations:** The knowledge base is small (8 entries + text file). A production system would use semantic embeddings. The agent's confidence score is not calibrated — it's a heuristic, not a probability.

**Collaboration with AI:** Claude helped me design the agentic loop architecture and suggested the hybrid deterministic + LLM approach (run exact math first, use LLM only for explanation). One incorrect suggestion: Claude initially suggested using `altair<5` in requirements, which is now incompatible with Streamlit ≥1.32 — I removed it.

---

## File Structure

```
applied-ai-system-project/
├── app.py                    # Streamlit UI (main entry point)
├── logic_utils.py            # Fixed game logic
├── ai_assistant.py           # RAG-augmented LLM hints and analysis
├── rag_retriever.py          # Two-source retrieval system
├── agent.py                  # Observe → Plan → Reason agentic loop
├── guardrails.py             # Input validation, sanitization, logging
├── evaluation.py             # Reliability metrics and scoring
├── requirements.txt
├── README.md
├── model_card.md
├── assets/
│   ├── architecture.md       # Mermaid diagram source
│   └── game_strategy_guide.txt  # RAG source 2 (editable text)
└── tests/
    ├── test_game_logic.py    # Unit tests for logic_utils
    ├── test_guardrails.py    # Unit tests for guardrails
    └── test_harness.py       # Full evaluation script (run directly)
```

---

*Built with Claude claude-haiku-4-5-20251001 | CodePath AI 110 — Foundations of AI Engineering*
