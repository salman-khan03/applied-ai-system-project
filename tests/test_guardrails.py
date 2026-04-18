"""Unit tests for guardrails (input validation, sanitization, rate limiting)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from guardrails import validate_guess_input, sanitize_ai_response, rate_limit_check


# ── validate_guess_input ──────────────────────────────────────────────────────

def test_valid_in_range():
    ok, err = validate_guess_input("50", 1, 100)
    assert ok and err is None


def test_boundary_low():
    ok, err = validate_guess_input("1", 1, 100)
    assert ok


def test_boundary_high():
    ok, err = validate_guess_input("100", 1, 100)
    assert ok


def test_out_of_range_above():
    ok, err = validate_guess_input("101", 1, 100)
    assert not ok


def test_out_of_range_below():
    ok, err = validate_guess_input("0", 1, 100)
    assert not ok


def test_negative_number():
    ok, err = validate_guess_input("-5", 1, 100)
    assert not ok


def test_empty_string():
    ok, err = validate_guess_input("", 1, 100)
    assert not ok


def test_none_input():
    ok, err = validate_guess_input(None, 1, 100)
    assert not ok


def test_too_long_input():
    ok, err = validate_guess_input("1" * 25, 1, 100)
    assert not ok


def test_non_numeric_word():
    ok, err = validate_guess_input("hello", 1, 100)
    assert not ok


def test_script_tag_blocked():
    ok, err = validate_guess_input("<script>", 1, 100)
    assert not ok


def test_decimal_accepted():
    ok, err = validate_guess_input("42.0", 1, 100)
    assert ok


# ── sanitize_ai_response ──────────────────────────────────────────────────────

def test_normal_text_passes():
    result = sanitize_ai_response("Try guessing 50 next!")
    assert result == "Try guessing 50 next!"


def test_script_injection_blocked():
    result = sanitize_ai_response("Hello <script>alert('xss')</script>")
    assert result == "Response filtered for safety."


def test_javascript_injection_blocked():
    result = sanitize_ai_response("javascript:void(0)")
    assert result == "Response filtered for safety."


def test_truncation_at_max_length():
    long_text = "A" * 600
    result = sanitize_ai_response(long_text, max_length=500)
    assert len(result) <= 504  # 500 chars + "..."


def test_empty_response():
    result = sanitize_ai_response("")
    assert result == "No response available."


def test_whitespace_only():
    result = sanitize_ai_response("   ")
    assert result == "No response available."


# ── rate_limit_check ──────────────────────────────────────────────────────────

def test_under_limit():
    ok, msg = rate_limit_check(5, max_per_game=15)
    assert ok and msg == ""


def test_at_limit():
    ok, msg = rate_limit_check(15, max_per_game=15)
    assert not ok


def test_over_limit():
    ok, msg = rate_limit_check(20, max_per_game=15)
    assert not ok


def test_zero_requests():
    ok, msg = rate_limit_check(0, max_per_game=15)
    assert ok
