from ast import (
    CharNode, 
    ConcatNode,
    OrNode,
    StarNode,
    PlusNode,
    QuestionNode
)

class State:
    _id_counter = 0

    def __init__(self):
        self.id = State._id_counter
        State._id_counter += 1

        self.transitions = {}
        self.epsilon = set()

    def add_transition(self, char, state):
        if char not in self.transitions:
            self.transitions[char] = set()
        self.transitions[char].add(state)

    def add_epsilon(self, state):
        self.epsilon.add(state)

    def __repr__(self):
        return f"State({self.id})"
    
class NFA:
    def __init__(self, start, accept):
        self.start = start
        self.accept = accept

def build_nfa(node):
    if isinstance(node,CharNode):
        return build_char(node)
    
    elif isinstance(node, ConcatNode):
        return build_concat(node)
    
    elif isinstance(node, OrNode):
        return build_or(node)
    
    elif isinstance(node, StarNode):
        return build_star(node)
    
    elif isinstance(node, PlusNode):
        return build_star(node)
    
    elif isinstance(node, QuestionNode):
        return build_question(node)
    
    else:
        raise TypeError(f"Unsupported AST node: {node}")
    
def build_char(node):
    start = State()
    accept = State()
    start.add_transition(node.value, accept)
    return NFA(start, accept)

def build_concat(node):
    left_nfa = build_nfa(node.left)
    right_nfa = build_nfa(node.right)

    left_nfa.accept.add_epsilon(right_nfa.start)

    return NFA(left_nfa.start, right_nfa.accept)

def build_or(node):
    start = State()
    accept = State()

    left_nfa = build_nfa(node.left)
    right_nfa = build_nfa(node.right)

    start.add_epsilon(left_nfa.start)
    start.add_epsilon(right_nfa.start)

    left_nfa.accept.add_epsilon(accept)
    right_nfa.accept.add_epsilon(accept)

    return NFA(start, accept)

def build_star(node):
    start = State()
    accept = State()

    child_nfa = build_nfa(node.child)

    start.add_epsilon(child_nfa.start)
    start.add_epsilon(accept)

    child_nfa.accept.add_epsilon(child_nfa.start)
    child_nfa.accept.add_epsilon(accept)

    return NFA(start, accept)

def build_plus(node):
    start = State()
    accept = State()

    child_nfa = build_nfa(node.child)

    start.add_epsilon(child_nfa.start)

    child_nfa.accept.add_epsilon(child_nfa.start)
    child_nfa.accept.add_epsilon(accept)

    return NFA(start, accept)

def build_question(node):
    start = State()
    accept = State()

    child_nfa = build_nfa(node.child)

    start.add_epsilon(child_nfa.start)
    start.add_epsilon(accept)

    child_nfa.accept.add_epsilon(accept)

    return NFA(start, accept)
