import pytest

import regex_engine

CASES = [
    # original demo
    ("a(b|c)*d", "ad", True),
    ("a(b|c)*d", "abd", True),
    ("a(b|c)*d", "acd", True),
    ("a(b|c)*d", "abbd", True),
    ("a(b|c)*d", "abcbcd", True),
    ("a(b|c)*d", "a", False),
    ("a(b|c)*d", "abc", False),
    ("a(b|c)*d", "abcdx", False),
    # plus (used to behave like star)
    ("a+", "", False),
    ("a+", "a", True),
    ("a+", "aaa", True),
    ("(ab)+", "abab", True),
    ("(ab)+", "aba", False),
    # question / empty
    ("ab?c", "ac", True),
    ("ab?c", "abc", True),
    ("ab?c", "abbc", False),
    ("", "", True),
    ("", "a", False),
    ("a|", "", True),
    ("a|", "a", True),
    ("()*", "", True),
    # classes, dot and escapes
    ("[a-z]+", "hello", True),
    ("[a-z]+", "Hello", False),
    ("[^0-9]+", "abc", True),
    ("[^0-9]+", "ab1", False),
    (r"\d+\.\d+", "3.14", True),
    (r"\d+\.\d+", "3x14", False),
    ("a.c", "abc", True),
    ("a.c", "a\nc", False),
    (r"\w+@\w+\.com", "bob_1@mail.com", True),
    (r"\s*x", "   x", True),
    (r"[a\-z]", "-", True),
    (r"[a\-z]", "b", False),
    ("[-a]", "-", True),
    ("[]a]", "]", True),
    (r"\(\)", "()", True),
    ("hello world", "hello world", True),
    (r"\*", "*", True),
]


@pytest.mark.parametrize("pattern, text, expected", CASES)
def test_fullmatch(pattern, text, expected):
    rx = regex_engine.compile(pattern)
    assert rx.fullmatch(text) is expected
    assert rx.dfa.matches(text) is expected


def test_trace_shape():
    rx = regex_engine.compile("ab")
    steps = rx.trace("ab")
    assert len(steps) == 3
    assert steps[0]["char"] is None
    assert steps[-1]["accepting"] is True
    assert steps[1]["char"] == "a"
