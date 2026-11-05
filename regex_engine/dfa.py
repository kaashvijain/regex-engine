"""Subset construction (NFA -> DFA) and Moore minimization.

The alphabet can be all of Unicode, so instead of individual characters the
DFA works over *symbol classes*: disjoint codepoint intervals such that every
character in one interval behaves the same way in every NFA transition.
"""

from bisect import bisect_right

from .charset import CharSet, MAX_CODEPOINT, describe_ranges
from .matcher import epsilon_closure

DEFAULT_MAX_STATES = 500


def alphabet_partition(charsets):
    """Split [0, MAX_CODEPOINT] into intervals at every charset boundary.

    Returns (starts, intervals): `starts` is a sorted list of interval
    start codepoints, used to look up the class of a character.
    """
    cuts = {0}
    for cs in charsets:
        for lo, hi in cs.ranges:
            cuts.add(lo)
            if hi + 1 <= MAX_CODEPOINT:
                cuts.add(hi + 1)
    starts = sorted(cuts)
    intervals = []
    for i, lo in enumerate(starts):
        hi = starts[i + 1] - 1 if i + 1 < len(starts) else MAX_CODEPOINT
        intervals.append((lo, hi))
    return starts, intervals


class DFA:
    def __init__(self, start, accepting, transitions, nfa_sets, starts, intervals, truncated):
        self.start = start                # state id
        self.accepting = accepting        # set of state ids
        self.transitions = transitions    # list[dict[class_index -> state id]]
        self.nfa_sets = nfa_sets          # list[frozenset[int]] NFA ids per DFA state
        self.starts = starts
        self.intervals = intervals
        self.truncated = truncated

    @property
    def num_states(self):
        return len(self.transitions)

    def class_of(self, ch):
        return bisect_right(self.starts, ord(ch)) - 1

    def matches(self, string):
        state = self.start
        for ch in string:
            state = self.transitions[state].get(self.class_of(ch))
            if state is None:
                return False
        return state in self.accepting

    def edges(self):
        """Grouped edges: list of (src, dst, CharSet) with classes merged."""
        out = []
        for src, trans in enumerate(self.transitions):
            by_dst = {}
            for cls, dst in trans.items():
                by_dst.setdefault(dst, []).append(self.intervals[cls])
            for dst, ranges in sorted(by_dst.items()):
                out.append((src, dst, CharSet(ranges)))
        return out


def build_dfa(nfa, max_states=DEFAULT_MAX_STATES, minimize=True):
    starts, intervals = alphabet_partition(nfa.charsets())
    # For each class, a representative character for testing transitions.
    reps = [chr(lo) for lo, _ in intervals]

    start_set = frozenset(epsilon_closure({nfa.start}))
    index = {start_set: 0}
    order = [start_set]
    transitions = [{}]
    truncated = False

    i = 0
    while i < len(order):
        current = order[i]
        # Only classes that some outgoing transition accepts can lead anywhere.
        for cls, rep in enumerate(reps):
            targets = set()
            for state in current:
                for cs, target in state.transitions:
                    if cs.matches(rep):
                        targets.add(target)
            if not targets:
                continue
            nxt = frozenset(epsilon_closure(targets))
            if nxt not in index:
                if len(order) >= max_states:
                    truncated = True
                    continue
                index[nxt] = len(order)
                order.append(nxt)
                transitions.append({})
            transitions[i][cls] = index[nxt]
        i += 1

    accepting = {idx for idx, s in enumerate(order) if nfa.accept in s}
    nfa_sets = [frozenset(st.id for st in s) for s in order]
    dfa = DFA(0, accepting, transitions, nfa_sets, starts, intervals, truncated)
    if minimize and not truncated:
        dfa = minimize_dfa(dfa)
    return dfa


def minimize_dfa(dfa):
    """Moore's partition refinement. Missing transitions go to an implicit dead state."""
    n = dfa.num_states
    DEAD = -1
    block = [1 if s in dfa.accepting else 0 for s in range(n)]
    classes = sorted({c for t in dfa.transitions for c in t})

    while True:
        signatures = {}
        new_block = []
        for s in range(n):
            sig = (block[s],) + tuple(
                block[dfa.transitions[s][c]] if c in dfa.transitions[s] else DEAD
                for c in classes
            )
            new_block.append(signatures.setdefault(sig, len(signatures)))
        if len(signatures) == len(set(block)):
            block = new_block
            break
        block = new_block

    # Renumber so the start state is 0 and others follow BFS order.
    remap = {}
    queue = [block[dfa.start]]
    remap[block[dfa.start]] = 0
    reps = {}
    for s in range(n):
        reps.setdefault(block[s], s)
    while queue:
        b = queue.pop(0)
        s = reps[b]
        for c in sorted(dfa.transitions[s]):
            nb = block[dfa.transitions[s][c]]
            if nb not in remap:
                remap[nb] = len(remap)
                queue.append(nb)

    m = len(remap)
    transitions = [{} for _ in range(m)]
    nfa_sets = [frozenset() for _ in range(m)]
    accepting = set()
    for s in range(n):
        b = block[s]
        if b not in remap:
            continue
        ns = remap[b]
        nfa_sets[ns] = nfa_sets[ns] | dfa.nfa_sets[s]
        if s in dfa.accepting:
            accepting.add(ns)
        for c, t in dfa.transitions[s].items():
            transitions[ns][c] = remap[block[t]]
    return DFA(0, accepting, transitions, nfa_sets, dfa.starts, dfa.intervals, dfa.truncated)


def describe_class(dfa, cls):
    return describe_ranges((dfa.intervals[cls],))
