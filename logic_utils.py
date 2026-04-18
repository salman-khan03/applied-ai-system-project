"""
Fixed game logic for Game Glitch Investigator.
Original bugs fixed:
  1. Inverted hints — guess > secret means "Too High" (Go LOWER), not the reverse
  2. All NotImplementedError stubs implemented
  3. Score clamped to minimum of 0
"""


def get_range_for_difficulty(difficulty: str) -> tuple[int, int]:
    """Return (low, high) inclusive range for the given difficulty."""
    match difficulty:
        case "Easy":
            return 1, 20
        case "Normal":
            return 1, 100
        case "Hard":
            return 1, 500
        case _:
            return 1, 100


def parse_guess(raw: str) -> tuple[bool, int | None, str | None]:
    """Parse raw text input into an integer guess."""
    if raw is None:
        return False, None, "Enter a guess."
    if raw.strip() == "":
        return False, None, "Enter a guess."
    try:
        value = int(float(raw.strip()))
    except (ValueError, OverflowError):
        return False, None, "That is not a number."
    return True, value, None


def check_guess(guess: int, secret: int) -> tuple[str, str]:
    """
    Compare guess to secret. Returns (outcome, message).
    Bug fix: guess > secret means answer is lower (Too High), not higher.
    """
    if guess == secret:
        return "Win", "Correct!"
    if guess > secret:
        return "Too High", "Go LOWER!"
    return "Too Low", "Go HIGHER!"


def update_score(current_score: int, outcome: str, attempt_number: int) -> int:
    """Update score. Win bonus decreases per attempt; wrong guesses cost 5 pts (min 0)."""
    match outcome:
        case "Win":
            return current_score + max(10, 100 - 10 * attempt_number)
        case "Too High" | "Too Low":
            return max(0, current_score - 5)
        case _:
            return current_score
