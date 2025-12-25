from enum import Enum, auto

class TokenType(Enum):
    CHAR = auto()           
    STAR = auto()           # *
    PLUS = auto()           # +
    QUESTION = auto()       # ?
    OR = auto()             # |
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    CONCAT = auto()         # implicit concatenation

class Token: 
    def __init__(self, type_, value = None):
        self.type = type_
        self.value = value #only for CHAR

    def __repr__(self):
        if self.value is not None:
            return f"{self.type.name}({self.value})"
        return f"{self.type.name}"
    
def tokenize(pattern: str):
    tokens = []

    for ch in pattern:
        if ch.isalnum():        #letters or digits
            tokens.append(Token(TokenType.CHAR, ch))
        elif ch == '*':
            tokens.append(Token(TokenType.STAR))
        elif ch == '+':
            tokens.append(Token(TokenType.PLUS))
        elif ch == '?':
            tokens.append(Token(TokenType.QUESTION))
        elif ch == '|':
            tokens.append(Token(TokenType.OR))
        elif ch == '(':
            tokens.append(Token(TokenType.LPAREN))
        elif ch == ')':
            tokens.append(Token(TokenType.RPAREN))
        else:
            raise ValueError(f"Unsupported character: {ch}")
        
    return tokens 

def insert_concat(tokens):
    result = []
    
    for i in range(len(tokens)):
        result.append(tokens[i])

        if i == len(tokens) - 1:
            break

        t1 = tokens[i]
        t2 = tokens[i+1]
        
        if(
            (t1.type in {
                TokenType.CHAR,
                TokenType.RPAREN,
                TokenType.STAR,
                TokenType.PLUS,
                TokenType.QUESTION,
                
            })
            and 
            (t2.type in {
                TokenType.CHAR,
                TokenType.LPAREN,
            })
        ):
            result.append(Token(TokenType.CONCAT))

    return result