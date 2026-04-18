# Model Card: Game Glitch Investigator AI Assistant

## Model Details

| Field | Value |
|-------|-------|
| Model | claude-haiku-4-5-20251001 (Anthropic) |
| Version | Haiku 4.5 |
| Access | Anthropic API |
| Prompt caching | Enabled on system prompts |
| Max tokens per call | 150 (hints), 200 (analysis), 250 (agent) |

## Intended Use

This AI assistant is embedded in an educational number guessing game. It serves three functions:

1. **Strategic hints** — Given the player's guess history and remaining attempts, the AI retrieves relevant strategy documents (RAG) and generates a 1–2 sentence hint grounded in the retrieved context.
2. **Post-game performance analysis** — After the game ends, the AI reviews the player's guessing pattern and explains whether their strategy was efficient (binary search) or suboptimal.
3. **Agentic planning** — A structured reasoning agent that observes the game state, plans the optimal next guess deterministically, and uses the LLM to explain its reasoning and assess risk.

## Limitations and Biases

- **Small knowledge base:** The RAG system uses 8 structured entries and one text file. It has no semantic search — retrieval is tag-based, so unusual queries may return irrelevant documents.
- **Hint spoiling:** The model may produce hints that are so specific they effectively reveal the secret number range to within a few values. The `no_secret_revealed` check only blocks exact matches.
- **Heuristic confidence:** The agent's confidence score is a heuristic (`2 / range_size`), not a calibrated probability. It should not be treated as statistically meaningful.
- **Language bias:** The model responds only in English. Non-English players are not supported.
- **Context length:** Hints are capped at 150 tokens, which can cause mid-sentence truncation for complex game states.
- **No memory across games:** The model has no session memory. Each game starts fresh with no knowledge of the player's past performance.

## Could This AI Be Misused?

This is a low-risk educational application. Potential misuse scenarios and mitigations:

| Risk | Mitigation |
|------|-----------|
| Prompt injection via guess input | `validate_guess_input()` rejects non-numeric input before it reaches the AI |
| Extracting API key from responses | Key is loaded from environment variable only; never included in prompts |
| Generating harmful content via game UI | System prompt constrains the model to game strategy only |
| Excessive API cost from automated spam | `rate_limit_check()` caps at 15 AI requests per session |
| XSS via AI-generated text in Streamlit | `sanitize_ai_response()` filters script tags and JS patterns |

## Testing Summary

**Unit tests:** 24 tests (pytest) — all pass without live API
**Test harness:** 11 scenario tests — all pass without live API
**Reliability evaluation (live API):** 3/3 trials passed in testing; avg hint relevance score: 0.75/1.0; avg latency: ~800ms

**What surprised me:** The relevance scorer caught that early hints (before any guesses) rarely mention specific range values — they score lower on `mentions_strategy` because they default to generic "start with the midpoint" advice. After the first 2 guesses, hint specificity (and relevance scores) improved significantly because the RAG retriever returns more targeted documents based on the current game state.

**One failure mode found:** When the player's valid range shrinks to 1–2 values, the agent's LLM reasoning step sometimes returns a confidence of 1.0 when it should be exactly 1.0 (the answer is determined), but occasionally the JSON parsing fails and the fallback returns 0.5. This is a known limitation of relying on LLM-generated JSON.

## AI Collaboration Notes

**Helpful suggestion:** When designing the agentic loop, Claude suggested separating the deterministic steps (observe: compute valid range; plan: pick midpoint) from the probabilistic step (reason: explain and assess risk). This hybrid approach made the agent reliable — it never fails to produce a valid recommendation even if the LLM returns invalid JSON, because the fallback uses the deterministic plan.

**Incorrect suggestion:** Claude suggested including `altair<5` in `requirements.txt` for Streamlit compatibility. This constraint is outdated — Streamlit ≥1.32 removed the Altair version dependency. Including it would cause installation conflicts. I removed it and verified the app runs correctly with Altair 5.x.

## Responsible Design Choices

- AI features **degrade gracefully** when the API key is not set — the game still works, guardrails still run, and the user sees a clear message rather than a crash.
- All AI calls are **logged** to `game.log` with timestamps, latency, and success/fail status, enabling post-hoc debugging.
- The model is used for **assistance only** — it never makes moves on the player's behalf without explicit button press.
- Retrieved documents are shown in the **sidebar knowledge base** panel so players can read the same sources the AI used, building trust through transparency.

## Portfolio Reflection

This project demonstrates that AI integration is most trustworthy when the AI's role is clearly scoped, its context is explicitly retrieved (not assumed), its outputs are validated before display, and the system fails safely when the AI is unavailable. As an AI engineer, I'm most proud of the hybrid deterministic + LLM agent design — it shows that "using AI" doesn't mean "trusting AI for everything."
