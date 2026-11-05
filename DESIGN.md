# Design: Signalbox

**Ink & paper.** A neutral off-white (or near-black) ground, ink-black line work, and a single cobalt accent that means "the machine is here right now". The diagrams carry the page; the chrome stays quiet.

## Tokens (`app/static/style.css` `:root`)

| Role | Light | Dark |
|---|---|---|
| Ground `--bg` | `#f7f7f5` | `#0f0f10` |
| Surface `--surface` / sunk `--sunk` | `#ffffff` / `#f0f0ed` | `#161618` / `#1c1c1f` |
| Lines `--line` / `--line-strong` | `#e4e4e0` / `#cbcbc6` | `#29292d` / `#3b3b41` |
| Ink `--ink` / `--ink-soft` / `--ink-faint` | `#111` / `#5e5e59` / `#8d8d87` | `#ededed` / `#a1a1a6` / `#75757b` |
| Accent `--accent` (active state, current step, focus) | cobalt `#2f5bff` | `#6d8bff` |
| Result `--ok` / `--fail` / `--warn` | `#1a7f37` / `#cf222e` / `#9a6700` | `#3fb950` / `#f85149` / `#d29922` |

Theme: follows `prefers-color-scheme` until the visitor picks one. The **Day / Night** pill in the header panel sets `data-theme` and saves the choice to localStorage.

## Type

- **Geist** (400–700): all UI text. The brand and the verdict word use tight negative tracking.
- **Geist Mono**: patterns, test strings, state IDs, edge labels, readouts and token chips. Use it only for code and data.

## Components

- **Header panel**: its own card at the top, holding the name, the tagline and the Day / Night pill. On phones the pill shows icons only.
- **Desk**: the pattern and test-string inputs (sunk fields with a 3px cobalt focus ring), the Full match / Search segmented control, example chips and a "Syntax" popover.
- **Traffic light (verdict)**: a near-black three-lamp signal head. Exactly one lamp glows: green for a match, red for no match or an invalid pattern, and yellow when search finds only empty matches. The verdict word and detail sit beside it in the same tone. It is vertical on desktop; on phones it is horizontal and moves to the top of the desk.
- **Diagram panel**: tabs with a cobalt underline on the selected one, a caption, and a `1:1` zoom toggle. The canvas has a dotted ground. Graphviz SVG is restyled by CSS:
  - `.lit` nodes are filled cobalt; `.lit.accepting` nodes are green.
  - `.edge.taken` edges are cobalt.
  - ε-edges are dashed in faint ink.
  - Parse-tree operator nodes are filled ink; leaf nodes are outlined.
- **Live parse tree**: in the Parse tree tab the step controls replay the parser. Nodes appear in creation order (`ast.build` from the API). The newest node is cobalt, and the pattern characters it covers are highlighted. The build replays whenever the tab opens or the pattern changes.
- **Input cells**: one mono cell per character. `.read` cells are faint, `.current` is cobalt, `.span` is a cobalt tint (parse tree), and `.matched` gets a green underline (search mode).
- **Step controls**: first (bar + double chevron), previous (chevron), play/pause (the round ink button), next (chevron), last (double chevron + bar), then a range slider. Keyboard: ← → Home End Space.

## Motion

- Lit states "pop" (scale 1.18 → 1 over 380 ms, expo ease-out).
- Parse-tree nodes rise in (400 ms).
- Playback runs at 650 ms per character, or 420 ms per parse node.
- `prefers-reduced-motion` turns animation off and skips the automatic parse replay.

## Rules

- Cobalt means only "current / active". Green, red and yellow are only for the verdict and for search matches.
- No new colours outside the tokens. Keep icons as inline SVG symbols with 1.8px strokes.
