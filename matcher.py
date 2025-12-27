from nfa import build_nfa
from tokenizer import tokenize, insert_concat
from parser import Parser

def epsilon_closure(states):
    stack = list(states)
    closure = set(states)

    while stack:
        state = stack.pop()
        for next_state in state.epsilon:
            if next_state not in closure:
                closure.add(next_state)
                stack.append(next_state)
    return closure

def move(states, char):
    result = set()
    for state in states:
        if char in state.transitions:
            result.update(state.transitions[char])
    return result

def match(nfa, string):
    current_states = epsilon_closure({nfa.start})

    for ch in string:
        current_states = move(current_states, ch)
        current_states = epsilon_closure(current_states)

    return nfa.accept in current_states

if __name__ == "__main__":
    pattern = "a(b|c)*d"

    tokens = insert_concat(tokenize(pattern))
    ast = Parser(tokens).parse()
    nfa = build_nfa(ast)

    tests = [
        "ad",
        "abd",
        "acd",
        "abbd",
        "abcbcd",
        "a",
        "abc",
        "abcdx"
    ]

    for s in tests:
        print(s, "->", match(nfa,s))