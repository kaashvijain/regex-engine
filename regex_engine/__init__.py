"""A small regex engine: tokenizer -> parser -> Thompson NFA -> (optional) DFA."""

from .errors import RegexSyntaxError
from .tokenizer import tokenize, insert_concat
from .parser import Parser
from .nfa import build_nfa
from .dfa import build_dfa
from . import matcher

__all__ = ["compile", "Regex", "RegexSyntaxError"]


class Regex:
    def __init__(self, pattern):
        self.pattern = pattern
        self.tokens = insert_concat(tokenize(pattern))
        self.ast = Parser(self.tokens, len(pattern)).parse()
        self.nfa = build_nfa(self.ast)
        self._dfa = None

    @property
    def dfa(self):
        if self._dfa is None:
            self._dfa = build_dfa(self.nfa)
        return self._dfa

    def fullmatch(self, string):
        return matcher.fullmatch(self.nfa, string)

    def search(self, string):
        return matcher.search(self.nfa, string)

    def finditer(self, string):
        return matcher.finditer(self.nfa, string)

    def findall(self, string):
        return [string[a:b] for a, b in self.finditer(string)]

    def trace(self, string, search=False):
        return matcher.trace(self.nfa, string, search)

    def __repr__(self):
        return f"Regex({self.pattern!r})"


def compile(pattern):
    return Regex(pattern)
