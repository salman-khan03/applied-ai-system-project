"""Unit tests for game logic (logic_utils.py)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logic_utils import check_guess, parse_guess, update_score, get_range_for_difficulty


# ── check_guess ───────────────────────────────────────────────────────────────

def test_winning_guess():
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"


def test_guess_too_high():
    outcome, _ = check_guess(60, 50)
    assert outcome == "Too High"


def test_guess_too_low():
    outcome, _ = check_guess(40, 50)
    assert outcome == "Too Low"


def test_guess_one_below_secret():
    outcome, _ = check_guess(49, 50)
    assert outcome == "Too Low"


def test_guess_one_above_secret():
    outcome, _ = check_guess(51, 50)
    assert outcome == "Too High"


def test_hint_not_inverted_high():
    """Regression: original bug had hints inverted."""
    _, message = check_guess(80, 50)
    assert "LOWER" in message


def test_hint_not_inverted_low():
    _, message = check_guess(20, 50)
    assert "HIGHER" in message


# ── parse_guess ───────────────────────────────────────────────────────────────

def test_parse_valid_integer():
    ok, val, err = parse_guess("42")
    assert ok and val == 42 and err is None


def test_parse_empty_string():
    ok, val, err = parse_guess("")
    assert not ok and val is None


def test_parse_none():
    ok, val, err = parse_guess(None)
    assert not ok


def test_parse_decimal_truncates():
    ok, val, err = parse_guess("3.7")
    assert ok and val == 3


def test_parse_non_numeric():
    ok, val, err = parse_guess("abc")
    assert not ok


def test_parse_whitespace():
    ok, val, err = parse_guess("   ")
    assert not ok


# ── update_score ──────────────────────────────────────────────────────────────

def test_score_win_attempt_1():
    score = update_score(0, "Win", 1)
    assert score == 90  # 100 - 10*1


def test_score_win_attempt_5():
    score = update_score(0, "Win", 5)
    assert score == 50  # 100 - 10*5


def test_score_win_floors_at_10():
    score = update_score(0, "Win", 15)
    assert score == 10  # clamped to minimum 10


def test_score_too_high_deducts():
    score = update_score(100, "Too High", 2)
    assert score == 95


def test_score_does_not_go_negative():
    score = update_score(3, "Too Low", 1)
    assert score == 0  # clamped to 0, not -2


# ── get_range_for_difficulty ──────────────────────────────────────────────────

def test_difficulty_easy():
    assert get_range_for_difficulty("Easy") == (1, 20)


def test_difficulty_normal():
    assert get_range_for_difficulty("Normal") == (1, 100)


def test_difficulty_hard():
    assert get_range_for_difficulty("Hard") == (1, 500)


def test_difficulty_unknown_defaults():
    assert get_range_for_difficulty("Unknown") == (1, 100)
