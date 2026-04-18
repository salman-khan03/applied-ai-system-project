"""
Fixed game logic for Game Glitch Investigator.
Original bugs fixed:
  1. Inverted hints (> vs < swapped)
  2. All NotImplementedError stubs implemented
  3. Score clamped to minimum of 0
"""


def get_range_for_difficulty(difficulty: str) -> tuple[int, int]:
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 500
    return 1, 100


def parse_guess(raw: str) -> tuple[bool, int | None, str | None]:
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
    """Returns (outcome, message). Bug fix: > means Too High, < means Too Low."""
    if guess == secret:
        return "Win", "🎉 Correct!"
    if guess > secret:
        return "Too High", "📉 Go LOWER!"
    return "Too Low", "📈 Go HIGHER!"


def update_score(current_score: int, outcome: str, attempt_number: int) -> int:
    if outcome == "Win":
        points = max(10, 100 - 10 * attempt_number)
        return current_score + points
    if outcome in ("Too High", "Too Low"):
        return max(0, current_score - 5)
    return current_score
