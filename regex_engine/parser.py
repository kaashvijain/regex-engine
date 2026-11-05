from .errors import RegexSyntaxError
from .tokenizer import TokenType
from .regex_ast import (
    CharNode,
    ConcatNode,
    EmptyNode,
    OrNode,
    StarNode,
    PlusNode,
    QuestionNode,
)

_POSTFIX = {
    TokenType.STAR: StarNode,
    TokenType.PLUS: PlusNode,
    TokenType.QUESTION: QuestionNode,
}

_SYMBOL = {
    TokenType.STAR: "*",
    TokenType.PLUS: "+",
    TokenType.QUESTION: "?",
    TokenType.OR: "|",
    TokenType.LPAREN: "(",
    TokenType.RPAREN: ")",
}


class Parser:
    """Recursive-descent parser.

    expression := term ('|' term)*
    term       := factor (CONCAT factor)*   |  <empty>
    factor     := atom ('*' | '+' | '?')*
    atom       := CHARSET | '(' expression ')'
    """

    def __init__(self, tokens, pattern_length=None):
        self.tokens = tokens
        self.pos = 0
        if pattern_length is None:
            pattern_length = (tokens[-1].pos + 1) if tokens else 0
        self.end_pos = pattern_length
        self.seq = 0  # creation counter, so the UI can replay the build

    def _made(self, node, start, end):
        """Stamp a freshly built node with its build order and pattern span."""
        node.order = self.seq
        node.span = (start, end)
        self.seq += 1
        return node

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _where(self):
        tok = self.current()
        return tok.pos if tok else self.end_pos

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        found = _SYMBOL.get(token.type, "a character") if token else "end of pattern"
        raise RegexSyntaxError(
            f"Expected '{_SYMBOL.get(token_type, token_type.name)}' but found {found}",
            self._where(),
        )

    def parse_expression(self):
        node = self.parse_term()
        while self.current() and self.current().type == TokenType.OR:
            self.eat(TokenType.OR)
            right = self.parse_term()
            node = self._made(OrNode(node, right), node.span[0], right.span[1])
        return node

    def parse_term(self):
        tok = self.current()
        # An empty alternative: '', 'a|', '|a', '()'
        if tok is None or tok.type in (TokenType.OR, TokenType.RPAREN):
            at = self._where()
            return self._made(EmptyNode(), at, at)

        node = self.parse_factor()
        while self.current() and self.current().type == TokenType.CONCAT:
            self.eat(TokenType.CONCAT)
            right = self.parse_factor()
            node = self._made(ConcatNode(node, right), node.span[0], right.span[1])
        return node

    def parse_factor(self):
        token = self.current()

        if token.type == TokenType.CHARSET:
            self.eat(TokenType.CHARSET)
            node = self._made(CharNode(token.value), token.pos, token.pos + len(token.text))
        elif token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.parse_expression()
            if self.current() is None:
                raise RegexSyntaxError("Unclosed group '('", token.pos)
            close = self.eat(TokenType.RPAREN)
            node.span = (token.pos, close.pos + 1)  # the group's node covers its parens
        elif token.type in _POSTFIX:
            raise RegexSyntaxError(
                f"'{_SYMBOL[token.type]}' has nothing to repeat", token.pos
            )
        else:
            raise RegexSyntaxError(
                f"Unexpected '{_SYMBOL.get(token.type, token.type.name)}'", token.pos
            )

        repeated = False
        while self.current() and self.current().type in _POSTFIX:
            tok = self.current()
            self.eat(tok.type)
            if repeated:
                raise RegexSyntaxError(
                    f"Multiple repeat operators: '{_SYMBOL[tok.type]}' follows another one",
                    tok.pos,
                )
            node = self._made(_POSTFIX[tok.type](node), node.span[0], tok.pos + 1)
            repeated = True
        return node

    def parse(self):
        node = self.parse_expression()
        tok = self.current()
        if tok is not None:
            if tok.type == TokenType.RPAREN:
                raise RegexSyntaxError("Unmatched ')'", tok.pos)
            raise RegexSyntaxError("Unexpected extra input", tok.pos)
        return node
