import pytest

import regex_engine
from regex_engine import RegexSyntaxError
from regex_engine.tokenizer import tokenize, insert_concat


def ast(p):
    return repr(regex_engine.compile(p).ast)


@pytest.mark.parametrize(
    "pattern, expected",
    [
        ("a", "Char(a)"),
        ("ab", "Concat(Char(a), Char(b))"),
        ("a|b", "Or(Char(a), Char(b))"),
        ("ab*", "Concat(Char(a), Star(Char(b)))"),
        ("(ab)+", "Plus(Concat(Char(a), Char(b)))"),
        ("a?", "Question(Char(a))"),
        ("", "Empty()"),
        ("a|", "Or(Char(a), Empty())"),
        ("()", "Empty()"),
        ("[a-c]", "Char([a-c])"),
        (r"\.", "Char(.)"),
        (".", "Char(.)"),
        (r"\d", r"Char(\d)"),
    ],
)
def test_ast_shapes(pattern, expected):
    assert ast(pattern) == expected


def test_concat_insertion():
    toks = insert_concat(tokenize("a(b)*c"))
    assert [t.type.name for t in toks] == [
        "CHARSET", "CONCAT", "LPAREN", "CHARSET", "RPAREN", "STAR", "CONCAT", "CHARSET",
    ]


@pytest.mark.parametrize(
    "pattern, position",
    [
        ("*a", 0),
        ("a(b", 1),
        ("a)", 1),
        ("(|*)", 2),
        ("a**", 2),
        ("[abc", 0),
        ("[z-a]", 1),
        ("a\\", 1),
        (r"\q", 0),
        ("a]", 1),
    ],
)
def test_syntax_errors(pattern, position):
    with pytest.raises(RegexSyntaxError) as info:
        regex_engine.compile(pattern)
    assert info.value.position == position


def test_state_ids_restart_per_pattern():
    a = regex_engine.compile("ab")
    b = regex_engine.compile("ab")
    assert [s.id for s in a.nfa.states] == [s.id for s in b.nfa.states]
    assert a.nfa.states[0].id == 0
