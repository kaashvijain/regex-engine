"""NFA simulation: full matching, step traces, and leftmost-longest search."""


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
        for charset, target in state.transitions:
            if charset.matches(char):
                result.add(target)
    return result


def match(nfa, string):
    """True if the whole string matches."""
    current = epsilon_closure({nfa.start})
    for ch in string:
        current = epsilon_closure(move(current, ch))
        if not current:
            return False
    return nfa.accept in current


fullmatch = match


def trace(nfa, string, search=False):
    """Active NFA states before any input and after each character.

    Returns a list of len(string)+1 steps. Step i is the set of states
    after consuming string[:i]. With search=True a new attempt starts at
    every position (the unanchored simulation), so `accepting` marks
    every index where some match ends.
    """
    start = epsilon_closure({nfa.start})
    current = start
    steps = [_step(nfa, current, 0, None)]
    for i, ch in enumerate(string):
        current = epsilon_closure(move(current, ch))
        if search:
            current |= start
        steps.append(_step(nfa, current, i + 1, ch))
    return steps


def _step(nfa, states, index, char):
    return {
        "index": index,
        "char": char,
        "states": sorted(s.id for s in states),
        "accepting": nfa.accept in states,
    }


def longest_match_at(nfa, string, start):
    """End index of the longest match beginning at `start`, or None."""
    current = epsilon_closure({nfa.start})
    last = start if nfa.accept in current else None
    i = start
    while current and i < len(string):
        current = epsilon_closure(move(current, string[i]))
        i += 1
        if nfa.accept in current:
            last = i
    return last


def finditer(nfa, string):
    """Yield non-overlapping (start, end) spans, leftmost-longest."""
    pos = 0
    n = len(string)
    while pos <= n:
        end = longest_match_at(nfa, string, pos)
        if end is None:
            pos += 1
            continue
        yield (pos, end)
        pos = end if end > pos else pos + 1


def search(nfa, string):
    """First (leftmost-longest) match span, or None."""
    return next(finditer(nfa, string), None)
