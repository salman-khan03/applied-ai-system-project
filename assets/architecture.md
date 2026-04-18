# System Architecture Diagram

## Mermaid.live Code

Copy everything between the triple-backtick fences below and paste it at
https://mermaid.live — then click "Export > PNG" and save as `assets/architecture.png`.

```mermaid
flowchart TD
    Player(["Player"])

    Player -->|"guess input"| GR["Guardrails
guardrails.py
validate + log"]

    GR -->|"valid input"| GL["Game Logic
logic_utils.py
check_guess / score"]

    GL -->|"outcome + log"| UI["Streamlit UI
app.py"]

    UI -->|"hint request + mode"| AI["AI Assistant
ai_assistant.py"]

    UI -->|"agent request"| AG["Agent Planner
agent.py"]

    AI -->|"1 retrieve tags"| RAG["RAG Retriever
rag_retriever.py"]

    RAG -->|"query"| KB1[("Knowledge Base
8 entries")]

    RAG -->|"read chunks"| KB2[("Strategy Guide
game_strategy_guide.txt")]

    RAG -->|"context docs"| AI

    AI -->|"2 mode selection"| SPEC["Specialization
Coach Mode
Analyst Mode
few-shot examples"]

    SPEC -->|"specialized prompt"| AI

    AI -->|"3 grounded prompt"| LLM["Claude Haiku 4.5
Anthropic API
prompt caching ON"]

    LLM -->|"hint text"| AI
    AI -->|"sanitized hint"| UI

    AG -->|"step 1 observe"| OB["Observe
compute valid range"]
    AG -->|"step 2 plan"| PL["Plan
binary search or trisect"]
    AG -->|"step 3 reason"| LLM
    LLM -->|"JSON plan"| AG
    AG -->|"recommendation"| UI

    GL -->|"log event"| LOG[("game.log")]
    AI -->|"log latency"| LOG
    GR -->|"log errors"| LOG

    UI -->|"post-game"| EVAL["Evaluation
evaluation.py
relevance + latency score"]

    EVAL -->|"metrics"| UI

    style LLM fill:#ff9900,color:#fff,stroke:#cc7700
    style KB1 fill:#4CAF50,color:#fff
    style KB2 fill:#4CAF50,color:#fff
    style LOG fill:#9E9E9E,color:#fff
    style SPEC fill:#9C27B0,color:#fff
```

## Architecture Summary

| Layer | Component | Purpose |
|-------|-----------|---------|
| Input | Guardrails | Validate input, block injection, log errors |
| Logic | Game Logic | Bug-fixed check_guess, update_score, parse_guess |
| Retrieval | RAG Retriever | Two sources: structured KB + text file |
| Specialization | AI Assistant | Few-shot Coach/Analyst modes constrain LLM tone |
| Planning | Agent | Observe → Plan → Reason with visible steps |
| Inference | Claude Haiku 4.5 | Shared LLM with prompt caching |
| Output | Streamlit UI | Two-column layout: game + AI panel |
| Reliability | Evaluation + Tests | 44 unit tests + 11 harness tests + live metrics |
