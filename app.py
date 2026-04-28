"""Game Glitch Investigator — Applied AI Edition.

Extended from Module 2 with RAG hints, few-shot specialization,
agentic planning, guardrails, and reliability logging.
"""

import random
import streamlit as st
from dotenv import load_dotenv
from google.genai.errors import ClientError
load_dotenv()

from logic_utils import get_range_for_difficulty, parse_guess, check_guess, update_score
from guardrails import (
    validate_guess_input,
    sanitize_ai_response,
    check_api_key_configured,
    rate_limit_check,
    log_guess,
    log_error,
)
from rag_retriever import retrieve_relevant_docs, format_tips_for_display
from ai_assistant import list_modes, get_mode_label, analyze_game_performance

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Game Glitch Investigator — AI Edition",
    page_icon="🎮",
    layout="wide",
)

api_ok, api_msg = check_api_key_configured()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("Settings")
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)

attempt_limits = {"Easy": 6, "Normal": 8, "Hard": 5}
attempt_limit = attempt_limits[difficulty]
low, high = get_range_for_difficulty(difficulty)
st.sidebar.caption(f"Range: **{low}-{high}** | Max attempts: **{attempt_limit}**")

st.sidebar.divider()
st.sidebar.subheader("AI Mode")
mode_keys = list_modes()
mode_labels = [get_mode_label(m) for m in mode_keys]
selected_label = st.sidebar.radio("Hint style:", mode_labels, index=0)
ai_mode = mode_keys[mode_labels.index(selected_label)]

_mode_desc = {
    "coach": "Encouraging tone with game analogies.",
    "analyst": "Precise, mathematical, probability-based.",
}
st.sidebar.caption(_mode_desc.get(ai_mode, ""))

st.sidebar.divider()
st.sidebar.subheader("AI Status")
if api_ok:
    st.sidebar.success("AI features enabled")
else:
    st.sidebar.warning("AI disabled — set GOOGLE_GEMINI_API_KEY")

st.sidebar.divider()
st.sidebar.subheader("Debug Knowledge Base")
tag_options = ["strategy", "binary_search", "range", "bug", "hard", "scoring", "guide"]
selected_tags = st.sidebar.multiselect("Filter tips:", tag_options, default=["strategy"])
if selected_tags:
    tips = retrieve_relevant_docs(selected_tags, top_k=2)
    st.sidebar.markdown(format_tips_for_display(tips))

# ── Session state init ────────────────────────────────────────────────────────
_defaults: dict = {
    "secret": None,
    "attempts": 0,
    "score": 0,
    "status": "playing",
    "history": [],
    "ai_hint": "",
    "ai_hint_mode": "",
    "ai_requests": 0,
    "agent_result": None,
    "post_analysis": "",
    "last_difficulty": difficulty,
}
for default_key, value in _defaults.items():
    if default_key not in st.session_state:
        st.session_state[default_key] = value

if st.session_state.last_difficulty != difficulty:
    for session_key in list(st.session_state.keys()):
        del st.session_state[session_key]
    st.rerun()

if st.session_state.secret is None:
    st.session_state.secret = random.randint(low, high)
    st.session_state.last_difficulty = difficulty


def reset_game() -> None:
    """Full game reset."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def _show_post_analysis(won: bool) -> None:
    if api_ok and not st.session_state.post_analysis:
        try:
            with st.spinner("Analyzing your performance..."):
                analysis = analyze_game_performance(
                    st.session_state.history,
                    st.session_state.secret,
                    won, low, high,
                )
                st.session_state.post_analysis = sanitize_ai_response(analysis)
        except (ImportError, RuntimeError, ValueError, TimeoutError, ClientError) as e:
            log_error("post_analysis", e)
            st.warning(f"AI analysis unavailable: {e}")
    if st.session_state.post_analysis:
        st.info(f"AI Review: {st.session_state.post_analysis}")


# ── Layout ────────────────────────────────────────────────────────────────────
st.title("Game Glitch Investigator - Applied AI Edition")
st.caption(
    "Module 2 base extended with RAG hints, few-shot specialization, "
    "agentic planning, and reliability guardrails."
)

col_game, col_ai = st.columns([3, 2])

# ── GAME COLUMN ───────────────────────────────────────────────────────────────
with col_game:
    st.subheader("Guess the Number")

    attempts_used = st.session_state.get("attempts", 0)
    attempts_left = attempt_limit - attempts_used

    st.info(
        f"Guess a number between **{low}** and **{high}**.  "
        f"Attempts left: **{attempts_left}** | Score: **{st.session_state.score}**"
    )

    with st.expander("Developer Debug Info"):
        st.write("Secret:", st.session_state.secret)
        st.write("Attempts used:", attempts_used)
        st.write("Score:", st.session_state.score)
        st.write("Status:", st.session_state.status)
        st.write("History:", st.session_state.history)

    raw_guess = st.text_input(
        "Enter your guess:",
        key=f"guess_input_{difficulty}_{attempts_used}",
        disabled=st.session_state.status != "playing",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        submit = st.button("Submit Guess", disabled=st.session_state.status != "playing")
    with c2:
        new_game = st.button("New Game")
    with c3:
        show_feedback = st.checkbox("Show feedback", value=True)

    if new_game:
        reset_game()

    # ── Game-over display ─────────────────────────────────────────────────────
    if st.session_state.status == "won":
        st.success(
            f"You won! The secret was **{st.session_state.secret}**.  "
            f"Final score: **{st.session_state.score}**"
        )
        _show_post_analysis(True)

    elif st.session_state.status == "lost":
        st.error(
            f"Out of attempts! The secret was **{st.session_state.secret}**.  "
            f"Score: **{st.session_state.score}**"
        )
        _show_post_analysis(False)

    # ── Submit handler ────────────────────────────────────────────────────────
    elif submit:
        valid, err = validate_guess_input(raw_guess, low, high)
        if not valid:
            st.error(err)
        else:
            st.session_state["attempts"] = st.session_state.get("attempts", 0) + 1
            _, guess_int, _ = parse_guess(raw_guess)

            outcome, message = check_guess(guess_int, st.session_state.secret)
            st.session_state.history.append({"guess": guess_int, "outcome": outcome})
            st.session_state.score = update_score(
                st.session_state.score, outcome, st.session_state["attempts"]
            )
            log_guess(guess_int, outcome, st.session_state["attempts"])

            st.session_state.ai_hint = ""
            st.session_state.ai_hint_mode = ""
            st.session_state.agent_result = None

            if outcome == "Win":
                st.session_state.status = "won"
                if show_feedback:
                    st.balloons()
                    st.success(message)
            elif st.session_state["attempts"] >= attempt_limit:
                st.session_state.status = "lost"
                if show_feedback:
                    st.error(message)
            elif show_feedback:
                st.warning(message)

    # ── Guess history ─────────────────────────────────────────────────────────
    if st.session_state.history:
        st.divider()
        st.subheader("Guess History")
        for i, entry in enumerate(st.session_state.history):
            icons = {"Win": "[WIN]", "Too High": "[HIGH]", "Too Low": "[LOW]"}
            icon = icons.get(entry["outcome"], "?")
            st.write(f"{icon} Attempt {i + 1}: **{entry['guess']}** -> {entry['outcome']}")

# ── AI COLUMN ─────────────────────────────────────────────────────────────────
with col_ai:
    st.subheader("AI Assistant")
    st.caption(f"Active mode: **{get_mode_label(ai_mode)}**")

    if not api_ok:
        st.warning(api_msg)
        st.markdown(
            "To enable AI features, set your API key:\n"
            "```\nexport GOOGLE_GEMINI_API_KEY=...\n```"
        )
    else:
        # ── RAG + few-shot hint ───────────────────────────────────────────────
        rate_ok, rate_msg = rate_limit_check(st.session_state["ai_requests"])
        HINT_DISABLED = not rate_ok or st.session_state.status != "playing"

        if st.button(
            "Get AI Hint (RAG + Specialized)",
            disabled=HINT_DISABLED,
            help="Retrieves strategy docs (RAG) then responds in your chosen mode (few-shot)",
        ):
            try:
                from ai_assistant import get_ai_hint
                label = get_mode_label(ai_mode)
                with st.spinner(f"Retrieving docs and generating {label} hint..."):
                    hint = get_ai_hint(
                        st.session_state.history,
                        low, high,
                        attempt_limit - st.session_state.attempts,
                        difficulty,
                        mode=ai_mode,
                    )
                    st.session_state.ai_hint = sanitize_ai_response(hint)
                    st.session_state.ai_hint_mode = label
                    st.session_state["ai_requests"] += 1
            except (ImportError, RuntimeError, ValueError, ClientError) as e:
                st.error(f"AI hint failed: {e}")

        if st.session_state.ai_hint:
            st.info(st.session_state.ai_hint)
            st.caption(
                f"Mode: {st.session_state.ai_hint_mode} | "
                f"Requests: {st.session_state['ai_requests']}/15"
            )

        st.divider()

        # ── Agentic planner ───────────────────────────────────────────────────
        st.subheader("Agentic Planner")
        AGENT_DISABLED = st.session_state.status != "playing"

        if st.button(
            "Run Agent (3-Step Plan)",
            disabled=AGENT_DISABLED,
            help="Observe -> Plan -> Reason loop with visible intermediate steps",
        ):
            try:
                from agent import run_agent
                with st.spinner("Running agent loop..."):
                    result = run_agent(st.session_state.history, low, high)
                    st.session_state.agent_result = result
            except (ImportError, RuntimeError, ValueError) as e:
                st.error(f"Agent failed: {e}")

        if st.session_state.agent_result:
            result = st.session_state.agent_result
            rec = result["final_recommendation"]
            vr = rec["valid_range"]

            st.metric("Valid Range", f"{vr[0]} - {vr[1]}")
            st.metric("Optimal Next Guess", rec["optimal_guess"])

            conf_pct = int(rec["confidence"] * 100)
            st.progress(conf_pct, text=f"Confidence: {conf_pct}%")

            risk_color = {"low": "green", "medium": "orange", "high": "red"}.get(
                rec["risk"], "gray"
            )
            st.markdown(
                f"Strategy: **{rec['strategy']}** | Risk: :{risk_color}[{rec['risk']}]"
            )

            with st.expander("View Agent Steps"):
                for step in result["steps"]:
                    st.json(step)

            if rec["reasoning"]:
                st.caption(f"Agent reasoning: {rec['reasoning']}")

st.divider()
st.caption(
    "Extended from Game Glitch Investigator (CodePath AI 110, Module 2) "
    "with gemini-2.0-flash-lite"
)
