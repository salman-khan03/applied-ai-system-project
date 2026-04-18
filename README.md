# Game Glitch Investigator: Applied AI System

## Base Project

**Original Project:** Game Glitch Investigator (CodePath AI110, Week 3 — Module 2 Debugging Lab)

The original project was a broken Streamlit number-guessing game with two intentional bugs: the secret number reset on every button click due to missing Streamlit session state, and the Higher/Lower hints were inverted (guessing too high told the player to go higher). The assignment was to find and fix the bugs, move logic into `logic_utils.py`, and write pytest tests to confirm the fixes.

**This Project 4 extension** evolves that debugged game into a full applied AI system by adding a RAG-powered hint engine, an observable agentic planner, two specialized AI modes, input/output guardrails, and a reliability evaluation layer.

---

## What the System Does

Players guess a secret number in a chosen difficulty range. At any point they can request an AI-generated hint (backed by retrieved strategy documents) or run an AI planning agent that observes the game state, computes the optimal next guess, and explains its reasoning. After the game ends, the AI delivers a post-game performance analysis. Every AI interaction is validated, logged, rate-limited, and scored for relevance.

---

## New AI Features

| Feature | What It Adds |
|---------|-------------|
| **RAG Hint Engine** | Retrieves relevant strategy documents from an 8-entry knowledge base and a text guide before generating a hint — grounds the response in real context rather than hallucinating |
| **Few-Shot Specialization** | Two selectable AI modes: Coach (encouraging, sports analogies) and Analyst (mathematical, probability-focused) — each mode uses a distinct system prompt plus 2 few-shot examples to constrain tone |
| **Agentic Planning Workflow** | Observable 3-step agent: (1) Observe — deterministically computes the valid range from guess history; (2) Plan — selects binary search or trisection strategy; (3) Reason — LLM explains the plan and rates confidence and risk |
| **Guardrails** | Input validation, response sanitization (blocks XSS/injection patterns), rate limiting (15 AI calls/game), and structured logging |
| **Reliability Evaluation** | Scores each AI hint on 4 dimensions: strategy mention, appropriate length, non-empty output, and secret not revealed. Runs live or offline. |

---

## System Architecture

![System Architecture Diagram](assets/architecture_diagram.png)

> **Note:** To regenerate the diagram, copy the Mermaid source from [assets/architecture.md](assets/architecture.md) into [mermaid.live](https://mermaid.live), then export as PNG and save as `assets/architecture_diagram.png`.

**Data flow summary:**

```
Player input
  → Guardrails (validate + log)
    → Game Logic (check_guess, update_score)
      → Streamlit UI (two-column layout)
        ├── AI Assistant → RAG Retriever (KB + text file)
        │                → Specialization (Coach/Analyst few-shot)
        │                → Claude Haiku 4.5 (prompt caching)
        └── Agent Planner → Observe → Plan → Claude Haiku 4.5 (JSON reasoning)
  → Evaluation (relevance + latency scoring)
  → game.log (all events timestamped)
```

| Layer | Component | File |
|-------|-----------|------|
| Input validation | Guardrails | `guardrails.py` |
| Game logic | Bug-fixed check/score/parse | `logic_utils.py` |
| Retrieval | Tag-based RAG (2 sources) | `rag_retriever.py` |
| Specialization | Few-shot Coach / Analyst modes | `ai_assistant.py` |
| Agentic planning | Observe → Plan → Reason | `agent.py` |
| Inference | Claude Haiku 4.5 w/ prompt caching | Anthropic API |
| UI | Streamlit wide-layout, session state | `app.py` |
| Reliability | Hint scoring + test harness | `evaluation.py` |

---

## Setup Instructions

**Prerequisites:** Python 3.9+, an Anthropic API key

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/applied-ai-system-project.git
cd applied-ai-system-project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key (AI features degrade gracefully without it — the game still works)
export ANTHROPIC_API_KEY="sk-ant-..."   # macOS/Linux
set ANTHROPIC_API_KEY=sk-ant-...        # Windows CMD

# 4. Run the app
python -m streamlit run app.py

# 5. (Optional) Run the test suite — no API key required
pytest tests/ -v
```

The app opens at `http://localhost:8501`. Select a difficulty, enter guesses in the left column, and use the AI panel on the right for hints or agent planning.

---

## Sample Interactions

### Interaction 1 — Coach Mode Hint (mid-game, Normal difficulty)

**Game state:** Secret is 73, player has guessed 50 (Too Low) and 75 (Too High). Valid range is now 51–74.

**Player clicks:** Get AI Hint (Coach mode selected)

**RAG retrieves:** `range_update` entry ("After each guess, eliminate the impossible half") + `binary_search` entry

**AI output:**
> "Great work narrowing it down — you've eliminated over 75% of the range already! Your valid zone is 51–74. If you pick the midpoint (62), you'll cut it in half again and close in fast. You've got this!"

**Hint relevance score:** 0.88 / 1.0 (mentions strategy, appropriate length, no secret revealed)

---

### Interaction 2 — Analyst Mode Hint (same state)

**Player clicks:** Get AI Hint (Analyst mode selected)

**AI output:**
> "Valid range: 51–74 (24 values remaining, down from 100). Optimal next guess: 62 (midpoint). Expected guesses to resolve: ≤2 with binary search. Probability of winning this turn if you guess 62: 4.2%."

---

### Interaction 3 — Agent Planner

**Player clicks:** Run Agent (after guesses 50 → Too Low, 75 → Too High)

**Agent Step 1 — Observe:**
```
valid_range: [51, 74]
range_size: 24
elimination_rate: 0.76
```

**Agent Step 2 — Plan:**
```
strategy: binary_search
optimal_guess: 62
steps_needed_to_win: 5
```

**Agent Step 3 — Reason (LLM):**
```json
{
  "reasoning": "Binary search is optimal for a 24-value range. Guessing 62 splits it evenly into [51,61] or [63,74].",
  "confidence": 0.92,
  "strategy_label": "Optimal",
  "risk_label": "Low"
}
```

**Final recommendation displayed in UI:** Guess 62 — Confidence: 0.92 — Strategy: Optimal — Risk: Low

---

### Interaction 4 — Guardrail Blocking Invalid Input

**Player enters:** `<script>alert(1)</script>`

**Guardrail response:** Input rejected immediately with message "Please enter a whole number."

**Logged to game.log:**
```
2026-04-18 03:48:57 | GUARDRAIL | input="<script>alert(1)</script>" | result=BLOCKED | reason=non_numeric
```

---

## Reliability and Testing

**Test suite:** 57 tests across 3 files — all pass without a live API key.

```
tests/test_game_logic.py    22 pytest tests   game logic, parsing, scoring, difficulty ranges
tests/test_guardrails.py    22 pytest tests   input validation, sanitization, rate limiting
tests/test_harness.py       13 scenario tests end-to-end scenarios, RAG, agent, evaluation
```

**Live API reliability (3 trials):**
- Success rate: 3/3 (100%)
- Average hint relevance score: 0.75 / 1.0
- Average latency: ~800ms

**Known failure mode:** When the valid range shrinks to 1–2 values, the agent's LLM reasoning step occasionally returns malformed JSON. The fallback uses the deterministic plan, so the system never crashes — but the confidence score defaults to 0.5 instead of the correct 1.0.

**What the guardrail examples show:**
- `validate_guess_input("<script>alert(1)</script>")` → blocked (non-numeric)
- `validate_guess_input("0")` → blocked (out of range [1, 100])
- `sanitize_ai_response("<script>steal()</script>")` → `[response blocked]`
- Rate limiter allows requests 1–14, blocks request 15+

---

## Design Decisions and Trade-offs

**Tag-based RAG over semantic search:** Simple and fast, no embedding model required. Trade-off: unusual queries may return irrelevant docs. Acceptable for a closed-domain game assistant with predictable query patterns.

**Hybrid deterministic + LLM agent:** Steps 1 and 2 (observe, plan) are pure math — they never fail. The LLM only handles step 3 (reasoning text). If the LLM returns bad JSON, the agent falls back to the deterministic plan. This means the agent is always useful even without an API key.

**Prompt caching on system prompts:** The system prompts are long (few-shot examples + mode instructions). Caching them reduces cost and latency on repeat calls in the same game session.

**Streamlit session state isolation:** When the player changes difficulty, the full session resets (new secret, cleared history, zeroed score). Without this, old guess history from a 1–20 game would pollute a new 1–500 game.

---

## Video Walkthrough

[INSERT LOOM LINK HERE — record a 5–7 min walkthrough showing: 2–3 full game inputs, AI hint behavior in both modes, agent planner output, and at least one guardrail block]

---

## Repository Structure

```
applied-ai-system-project/
├── app.py                  Main Streamlit application
├── logic_utils.py          Bug-fixed game logic
├── guardrails.py           Input validation, sanitization, rate limiting, logging
├── ai_assistant.py         RAG + few-shot specialization (Coach / Analyst modes)
├── rag_retriever.py        Two-source RAG retriever (KB + text file)
├── agent.py                Observable 3-step agentic planner
├── evaluation.py           Hint relevance scoring + reliability evaluation
├── model_card.md           AI model documentation, limitations, testing results
├── reflection.md           Development reflection
├── requirements.txt
├── assets/
│   ├── architecture.md         Mermaid source for system diagram
│   ├── architecture_diagram.png  System architecture PNG (export from Mermaid Live)
│   └── game_strategy_guide.txt RAG knowledge source
└── tests/
    ├── test_game_logic.py
    ├── test_guardrails.py
    └── test_harness.py
```
