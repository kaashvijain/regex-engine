# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
FastAPI backend (`app/server.py`) serving a plain static HTML/CSS/JS frontend (`app/static/`), with no build step. Graphs are rendered in the browser from server-generated Graphviz DOT using viz-js.

## Users
- **Learners**: students of automata theory and compilers who want to see how a regex becomes an NFA and a DFA, and how matching proceeds one character at a time.
- **Portfolio viewers**: engineers and recruiters assessing the author's work. They should grasp it and be impressed within about 30 seconds.
- **Developers**: people who want to check that a pattern matches what they expect.

## Product Purpose
A from-scratch regex engine (tokenizer → recursive-descent parser → Thompson NFA → subset-construction DFA with minimization) that shows its own internals. Success means a visitor types a pattern and *watches* the machine work: tokens, the AST, the NFA and DFA graphs, and a step-through simulation.

## Positioning
Unlike regex testers that treat the engine as a black box (regex101 and similar), every stage here is the author's own implementation and is exposed. The visualization *is* the engine, not an illustration of it.

## Capabilities and Constraints
- Syntax: literals, `.`, escapes (`\d \w \s \D \W \S \n \t`, escaped metacharacters), `[...]` classes with ranges and negation, `* + ?`, `|`, and groups `( )`. No anchors, backreferences, lazy quantifiers or `{n,m}`.
- Modes: full match, and search (leftmost-longest, non-overlapping).
- Limits: pattern ≤ 200 chars, text ≤ 2000 chars, DFA capped at 300 states (shown as truncated).
- Syntax errors come with a character position.

## Evidence on Hand
No testimonials, users or metrics exist. Do not invent any.

## Product Principles
1. Show the mechanism. Every result should be traceable to the states that produced it.
2. Instant feedback: typing updates everything, with no submit button.
3. Learnable without leaving the page. Syntax help and plain-language explanations sit next to the work.
4. Honest about limits. Unsupported syntax gets a clear, positioned error.
