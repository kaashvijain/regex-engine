from tokenizer import TokenType

from ast import(
    ASTNode,
    CharNode,
    ConcatNode,
    OrNode,
    StarNode,
    PlusNode,
    QuestionNode
)

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        raise SyntaxError(f"Expected {token_type}, got {token}")  
    
    def parse_expression(self):
        node = self.parse_term()

        while self.current() and self.current().type == TokenType.OR:
            self.eat(TokenType.OR)
            right = self.parse_term()
            node = OrNode(node, right)

        return node
    
    def parse_term(self):
        node = self.parse_factor()
        
        while self.current() and self.current().type == TokenType.CONCAT:
            self.eat(TokenType.CONCAT)
            right = self.parse_factor()
            node = ConcatNode(node, right)

        return node
    
    def parse_factor(self):
        token = self.current()

        if token.type == TokenType.CHAR:
            self.eat(TokenType.CHAR)
            node = CharNode(token.value)

        elif token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.parse_expression()
            self.eat(TokenType.RPAREN)

        else:
            raise SyntaxError(f"Unexpected token: {token}")
        
        #for postfix operators 
        while self.current() and self.current().type in {
            TokenType.STAR,
            TokenType.PLUS,
            TokenType.QUESTION
        }:
            if self.current().type == TokenType.STAR:
                self.eat(TokenType.STAR)
                node = StarNode(node)
            elif self.current().type == TokenType.PLUS:
                self.eat(TokenType.PLUS)
                node = PlusNode(node)
            elif self.current().type == TokenType.QUESTION:
                self.eat(TokenType.QUESTION)
                node = QuestionNode(node)
        
        return node
    
    def parse(self):
        node = self.parse_expression()
        if self.current() is not None:
            raise SyntaxError("Unexpected extra tokens")
        return node
    