"""Cross-check the engine against Python's `re` and the NFA against the DFA."""

import itertools
import random
import re

import pytest

import regex_engine

ALPHABET = "abc"
STRINGS = [""] + [
    "".join(p) for n in range(1, 5) for p in itertools.product(ALPHABET, repeat=n)
]

CORPUS = [
    "a", "ab", "a|b", "a*", "a+", "a?", "(ab)*", "(a|b)*c", "a(b|c)*", "(a|)+",
    "((a|b)c)*", "a*b*c*", "(a*)*", "(a|b|c)+b", "[ab]c?", "[^a]+", ".a.", "(a?b)+",
    "a|b*|c", "(ab|a)(bc|c)",
]


def check(pattern):
    rx = regex_engine.compile(pattern)
    dfa = rx.dfa
    py = re.compile(pattern)
    for s in STRINGS:
        expected = py.fullmatch(s) is not None
        assert rx.fullmatch(s) == expected, (pattern, s)
        assert dfa.matches(s) == expected, (pattern, s, "dfa")


@pytest.mark.parametrize("pattern", CORPUS)
def test_corpus(pattern):
    check(pattern)


def random_pattern(rng, depth=0):
    choice = rng.random()
    if depth > 3 or choice < 0.3:
        return rng.choice(["a", "b", "c", ".", "[ab]", "[^c]"])
    if choice < 0.55:
        return random_pattern(rng, depth + 1) + random_pattern(rng, depth + 1)
    if choice < 0.75:
        return "(" + random_pattern(rng, depth + 1) + "|" + random_pattern(rng, depth + 1) + ")"
    return "(" + random_pattern(rng, depth + 1) + ")" + rng.choice("*+?")


def test_random_fuzz():
    rng = random.Random(1234)
    for _ in range(300):
        check(random_pattern(rng))
