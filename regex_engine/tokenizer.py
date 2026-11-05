from enum import Enum, auto

from .charset import CharSet, CLASS_ESCAPES, CHAR_ESCAPES, DOT
from .errors import RegexSyntaxError


class TokenType(Enum):
    CHARSET = auto()        # a literal, '.', escape or [...] class
    STAR = auto()           # *
    PLUS = auto()           # +
    QUESTION = auto()       # ?
    OR = auto()             # |
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    CONCAT = auto()         # implicit concatenation


class Token:
    def __init__(self, type_, value=None, pos=0, text=""):
        self.type = type_
        self.value = value  # CharSet, only for CHARSET
        self.pos = pos      # index in the pattern
        self.text = text    # source text of the token

    def __repr__(self):
        if self.value is not None:
            return f"{self.type.name}({self.value.label()})"
        return f"{self.type.name}"


_SIMPLE = {
    "*": TokenType.STAR,
    "+": TokenType.PLUS,
    "?": TokenType.QUESTION,
    "|": TokenType.OR,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
}


def _read_escape(pattern, i):
    """`pattern[i]` is a backslash. Returns (CharSet, next_index)."""
    if i + 1 >= len(pattern):
        raise RegexSyntaxError("Pattern ends with a lone backslash", i)
    e = pattern[i + 1]
    if e in CLASS_ESCAPES:
        return CLASS_ESCAPES[e], i + 2
    if e in CHAR_ESCAPES:
        return CharSet.char(CHAR_ESCAPES[e]), i + 2
    if e.isalnum():
        raise RegexSyntaxError(f"Unknown escape \\{e}", i)
    return CharSet.char(e), i + 2


def _read_class(pattern, start):
    """`pattern[start]` is '['. Returns (CharSet, next_index)."""
    i = start + 1
    negated = False
    if i < len(pattern) and pattern[i] == "^":
        negated = True
        i += 1

    parts = []
    first = True
    while True:
        if i >= len(pattern):
            raise RegexSyntaxError("Unclosed character class '['", start)
        ch = pattern[i]
        if ch == "]" and not first:
            i += 1
            break
        first = False

        # read one class atom
        if ch == "\\":
            atom, i = _read_escape(pattern, i)
        else:
            atom, i = CharSet.char(ch), i + 1

        # range a-z
        is_single = len(atom.ranges) == 1 and atom.ranges[0][0] == atom.ranges[0][1]
        if (
            is_single
            and i + 1 < len(pattern)
            and pattern[i] == "-"
            and pattern[i + 1] != "]"
        ):
            range_pos = i
            if pattern[i + 1] == "\\":
                end, i = _read_escape(pattern, i + 1)
            else:
                end, i = CharSet.char(pattern[i + 1]), i + 2
            if not (len(end.ranges) == 1 and end.ranges[0][0] == end.ranges[0][1]):
                raise RegexSyntaxError("Invalid range end in character class", range_pos)
            lo, hi = atom.ranges[0][0], end.ranges[0][0]
            if lo > hi:
                raise RegexSyntaxError(
                    f"Invalid range {chr(lo)}-{chr(hi)}: start is after end", range_pos - 1
                )
            atom = CharSet([(lo, hi)])
        parts.append(atom)

    cs = CharSet.union(parts, negated=negated)
    return cs, i


def tokenize(pattern: str):
    tokens = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch in _SIMPLE:
            tokens.append(Token(_SIMPLE[ch], pos=i, text=ch))
            i += 1
        elif ch == "\\":
            cs, j = _read_escape(pattern, i)
            tokens.append(Token(TokenType.CHARSET, cs, i, pattern[i:j]))
            i = j
        elif ch == "[":
            cs, j = _read_class(pattern, i)
            tokens.append(Token(TokenType.CHARSET, cs, i, pattern[i:j]))
            i = j
        elif ch == ".":
            tokens.append(Token(TokenType.CHARSET, DOT, i, "."))
            i += 1
        elif ch == "]":
            raise RegexSyntaxError("Unmatched ']' (escape it as \\])", i)
        else:
            tokens.append(Token(TokenType.CHARSET, CharSet.char(ch), i, ch))
            i += 1
    return tokens


_CONCAT_LEFT = {
    TokenType.CHARSET,
    TokenType.RPAREN,
    TokenType.STAR,
    TokenType.PLUS,
    TokenType.QUESTION,
}
_CONCAT_RIGHT = {TokenType.CHARSET, TokenType.LPAREN}


def insert_concat(tokens):
    result = []
    for i, t1 in enumerate(tokens):
        result.append(t1)
        if i + 1 < len(tokens):
            t2 = tokens[i + 1]
            if t1.type in _CONCAT_LEFT and t2.type in _CONCAT_RIGHT:
                result.append(Token(TokenType.CONCAT, pos=t2.pos, text=""))
    return result
