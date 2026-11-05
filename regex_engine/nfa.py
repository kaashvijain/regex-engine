"""Thompson construction: AST -> NFA."""

from .regex_ast import (
    CharNode,
    ConcatNode,
    EmptyNode,
    OrNode,
    StarNode,
    PlusNode,
    QuestionNode,
)


class State:
    def __init__(self, id_):
        self.id = id_
        self.transitions = []   # list of (CharSet, State)
        self.epsilon = []       # list of State (ordered, for stable rendering)

    def add_transition(self, charset, state):
        self.transitions.append((charset, state))

    def add_epsilon(self, state):
        if state not in self.epsilon:
            self.epsilon.append(state)

    def __repr__(self):
        return f"State({self.id})"


class NFA:
    def __init__(self, start, accept, states):
        self.start = start
        self.accept = accept
        self.states = states  # all states, indexed by id

    def charsets(self):
        return [cs for s in self.states for cs, _ in s.transitions]


class _Fragment:
    def __init__(self, start, accept):
        self.start = start
        self.accept = accept


class NFABuilder:
    """Builds an NFA with state ids numbered from 0 for each pattern."""

    def __init__(self):
        self.states = []

    def new_state(self):
        s = State(len(self.states))
        self.states.append(s)
        return s

    def build(self, node):
        if isinstance(node, CharNode):
            return self.build_char(node)
        if isinstance(node, EmptyNode):
            return self.build_empty(node)
        if isinstance(node, ConcatNode):
            return self.build_concat(node)
        if isinstance(node, OrNode):
            return self.build_or(node)
        if isinstance(node, StarNode):
            return self.build_star(node)
        if isinstance(node, PlusNode):
            return self.build_plus(node)
        if isinstance(node, QuestionNode):
            return self.build_question(node)
        raise TypeError(f"Unsupported AST node: {node}")

    def build_char(self, node):
        start = self.new_state()
        accept = self.new_state()
        start.add_transition(node.value, accept)
        return _Fragment(start, accept)

    def build_empty(self, node):
        start = self.new_state()
        accept = self.new_state()
        start.add_epsilon(accept)
        return _Fragment(start, accept)

    def build_concat(self, node):
        left = self.build(node.left)
        right = self.build(node.right)
        left.accept.add_epsilon(right.start)
        return _Fragment(left.start, right.accept)

    def build_or(self, node):
        start = self.new_state()
        left = self.build(node.left)
        right = self.build(node.right)
        accept = self.new_state()

        start.add_epsilon(left.start)
        start.add_epsilon(right.start)
        left.accept.add_epsilon(accept)
        right.accept.add_epsilon(accept)
        return _Fragment(start, accept)

    def build_star(self, node):
        start = self.new_state()
        child = self.build(node.child)
        accept = self.new_state()

        start.add_epsilon(child.start)
        start.add_epsilon(accept)
        child.accept.add_epsilon(child.start)
        child.accept.add_epsilon(accept)
        return _Fragment(start, accept)

    def build_plus(self, node):
        start = self.new_state()
        child = self.build(node.child)
        accept = self.new_state()

        start.add_epsilon(child.start)
        child.accept.add_epsilon(child.start)
        child.accept.add_epsilon(accept)
        return _Fragment(start, accept)

    def build_question(self, node):
        start = self.new_state()
        child = self.build(node.child)
        accept = self.new_state()

        start.add_epsilon(child.start)
        start.add_epsilon(accept)
        child.accept.add_epsilon(accept)
        return _Fragment(start, accept)


def build_nfa(node):
    builder = NFABuilder()
    frag = builder.build(node)
    return NFA(frag.start, frag.accept, builder.states)
