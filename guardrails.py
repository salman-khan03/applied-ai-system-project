"""
Input validation, response sanitization, rate limiting, and logging guardrails.
Every AI request and player action is logged to game.log.
"""

import re
import logging
import os
from datetime import datetime

# Configure file logger
logging.basicConfig(
    filename="game.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("game_glitch")


def validate_guess_input(raw: str, low: int, high: int) -> tuple[bool, str | None]:
    """Validate player input. Returns (is_valid, error_message)."""
    if raw is None or raw.strip() == "":
        return False, "Please enter a number."

    if len(raw) > 20:
        return False, "Input too long. Enter a reasonable number."

    if not re.match(r"^-?\d+(\.\d+)?$", raw.strip()):
        return False, "Invalid input. Please enter a whole number."

    try:
        value = int(float(raw.strip()))
    except (ValueError, OverflowError):
        return False, "That number is too large to process."

    if value < 0:
        return False, f"Enter a positive number between {low} and {high}."

    if value < low or value > high:
        return False, f"Number must be between {low} and {high}."

    return True, None


def sanitize_ai_response(text: str, max_length: int = 500) -> str:
    """Remove injection artifacts and truncate overly long AI responses."""
    if not text or not text.strip():
        return "No response available."

    suspicious = ["<script", "javascript:", "eval(", "__import__", "os.system"]
    for pattern in suspicious:
        if pattern.lower() in text.lower():
            logger.warning("AI response filtered: suspicious pattern '%s'", pattern)
            return "Response filtered for safety."

    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text.strip()


def check_api_key_configured() -> tuple[bool, str]:
    key = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
    if not key:
        return False, "GOOGLE_GEMINI_API_KEY not set. AI features disabled."
    return True, "API key configured."


def rate_limit_check(request_count: int, max_per_game: int = 15) -> tuple[bool, str]:
    if request_count >= max_per_game:
        return False, f"AI request limit reached ({max_per_game} per game)."
    return True, ""


def log_guess(guess: int, outcome: str, attempt: int) -> None:
    logger.info("GUESS | attempt=%d guess=%d outcome=%s", attempt, guess, outcome)


def log_ai_request(request_type: str, latency_ms: float, success: bool, detail: str = "") -> None:
    status = "OK" if success else "FAIL"
    logger.info(
        "AI_REQUEST | type=%s status=%s latency_ms=%.0f %s",
        request_type, status, latency_ms, detail,
    )


def log_error(context: str, error: Exception) -> None:
    logger.error("ERROR | context=%s error=%s", context, str(error))
