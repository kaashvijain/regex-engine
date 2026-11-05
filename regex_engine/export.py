"""Serialize tokens, AST, NFA and DFA to JSON-friendly dicts and Graphviz DOT."""

from .regex_ast import (
    CharNode,
    ConcatNode,
    EmptyNode,
    OrNode,
    StarNode,
    PlusNode,
    QuestionNode,
)


def tokens_to_json(tokens):
    out = []
    for t in tokens:
        item = {"type": t.type.name, "pos": t.pos, "text": t.text}
        if t.value is not None:
            item["label"] = t.value.label()
        out.append(item)
    return out


def ast_to_json(node):
    if isinstance(node, CharNode):
        return {"type": "Char", "label": node.value.label(), "children": []}
    if isinstance(node, EmptyNode):
        return {"type": "Empty", "label": "ε", "children": []}
    if isinstance(node, (ConcatNode, OrNode)):
        # Flatten chains (a·b·c) so the tree stays readable.
        kind = type(node)
        children = []

        def collect(n):
            if isinstance(n, kind):
                collect(n.left)
                collect(n.right)
            else:
                children.append(ast_to_json(n))

        collect(node)
        name = "Concat" if kind is ConcatNode else "Or"
        return {"type": name, "label": "·" if name == "Concat" else "|", "children": children}
    for kind, name, sym in (
        (StarNode, "Star", "*"),
        (PlusNode, "Plus", "+"),
        (QuestionNode, "Question", "?"),
    ):
        if isinstance(node, kind):
            return {"type": name, "label": sym, "children": [ast_to_json(node.child)]}
    raise TypeError(f"Unsupported AST node: {node}")


def _dot_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


_GRAPH_HEADER = (
    "digraph G {\n"
    '  rankdir=LR; bgcolor="transparent"; pad=0.2; nodesep=0.35; ranksep=0.45;\n'
    '  node [shape=circle, fontname="monospace", fontsize=12, width=0.42, fixedsize=true];\n'
    '  edge [fontname="monospace", fontsize=12, arrowsize=0.7];\n'
    '  __start [shape=point, width=0.01, style=invis, label=""];\n'
)


def _nfa_edges(nfa):
    """All NFA edges in a stable order: (src, dst, CharSet or None for ε)."""
    edges = []
    for s in nfa.states:
        for cs, t in s.transitions:
            edges.append((s, t, cs))
        for t in s.epsilon:
            edges.append((s, t, None))
    return edges


def nfa_to_json(nfa):
    edges = [
        {"id": i, "from": s.id, "to": t.id, "label": cs.label() if cs else "ε", "epsilon": cs is None}
        for i, (s, t, cs) in enumerate(_nfa_edges(nfa))
    ]
    return {
        "states": len(nfa.states),
        "start": nfa.start.id,
        "accept": nfa.accept.id,
        "edges": edges,
        "dot": nfa_to_dot(nfa),
    }


def nfa_to_dot(nfa):
    lines = [_GRAPH_HEADER]
    for s in nfa.states:
        shape = "doublecircle" if s is nfa.accept else "circle"
        lines.append(f'  s{s.id} [id="nfa-{s.id}", label="{s.id}", shape={shape}];\n')
    lines.append(f'  __start -> s{nfa.start.id} [id="nfa-entry"];\n')
    for i, (s, t, cs) in enumerate(_nfa_edges(nfa)):
        if cs is None:
            lines.append(
                f'  s{s.id} -> s{t.id} [id="nfa-e{i}", label="ε", style=dashed, class="eps"];\n'
            )
        else:
            lines.append(
                f'  s{s.id} -> s{t.id} [id="nfa-e{i}", label="{_dot_escape(cs.label())}", class="sym"];\n'
            )
    lines.append("}\n")
    return "".join(lines)


def annotate_trace(nfa, dfa, steps, text, search=False):
    """Add, per step, the NFA symbol edges just taken and the DFA state reached.

    The DFA recognises whole strings, so in search mode `dfa` is None.
    """
    edges = list(enumerate(_nfa_edges(nfa)))
    dfa_state = None if search else dfa.start
    for i, step in enumerate(steps):
        if i == 0:
            step["taken"] = []
        else:
            prev = set(steps[i - 1]["states"])
            ch = text[i - 1]
            step["taken"] = [
                idx for idx, (s, t, cs) in edges
                if cs is not None and s.id in prev and cs.matches(ch)
            ]
            if dfa_state is not None:
                dfa_state = dfa.transitions[dfa_state].get(dfa.class_of(ch))
        step["dfa"] = dfa_state
    return steps


def ast_to_dot(node):
    """Top-down tree drawing of the (flattened) AST."""
    tree = ast_to_json(node)
    lines = [
        "digraph AST {\n",
        '  bgcolor="transparent"; pad=0.2; nodesep=0.3; ranksep=0.4;\n',
        '  node [shape=box, style=rounded, fontname="monospace", fontsize=12, height=0.36, margin="0.18,0.05"];\n',
        "  edge [arrowhead=none];\n",
    ]
    counter = [0]

    def walk(n):
        nid = counter[0]
        counter[0] += 1
        label = n["label"] if n["type"] in ("Char", "Empty") else f'{n["label"]} {n["type"].lower()}'
        kind = "leaf" if not n["children"] else "op"
        lines.append(f'  a{nid} [id="ast-{nid}", label="{_dot_escape(label)}", class="{kind}"];\n')
        for c in n["children"]:
            cid = walk(c)
            lines.append(f"  a{nid} -> a{cid};\n")
        return nid

    walk(tree)
    lines.append("}\n")
    return "".join(lines)


def dfa_to_json(dfa):
    edges = [
        {"from": a, "to": b, "label": cs.label()} for a, b, cs in dfa.edges()
    ]
    return {
        "states": dfa.num_states,
        "start": dfa.start,
        "accepting": sorted(dfa.accepting),
        "nfa_sets": [sorted(s) for s in dfa.nfa_sets],
        "edges": edges,
        "truncated": dfa.truncated,
        "dot": dfa_to_dot(dfa),
    }


def dfa_to_dot(dfa):
    lines = [_GRAPH_HEADER]
    for s in range(dfa.num_states):
        shape = "doublecircle" if s in dfa.accepting else "circle"
        tip = "NFA states {" + ", ".join(map(str, sorted(dfa.nfa_sets[s]))) + "}"
        lines.append(
            f'  d{s} [id="dfa-{s}", label="{s}", shape={shape}, tooltip="{tip}"];\n'
        )
    lines.append(f'  __start -> d{dfa.start} [id="dfa-entry"];\n')
    for a, b, cs in dfa.edges():
        lines.append(f'  d{a} -> d{b} [label="{_dot_escape(cs.label())}"];\n')
    lines.append("}\n")
    return "".join(lines)
