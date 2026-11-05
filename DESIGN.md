# Design: Signalbox

The UI is a **railway signal-box mimic panel**. The automaton is drawn as track, states are lamps, the input string is a train-describer readout, and the match result is a three-aspect signal. Everything new should be expressed in that vocabulary.

## Tokens (`app/static/style.css` `:root`)

| Role | Light (day panel) | Dark (night panel) |
|---|---|---|
| Panel ground `--panel` | `#c3cbbf` grey-green | `#151a17` |
| Raised / sunk | `--panel-raised` / `--panel-sunk` | same names |
| Engraved plate `--plate` / `--plate-ink` | `#1a1f1b` / `#eef0e6` | `#0a0d0b` / `#e8ebe1` |
| Track `--track` / ε-track `--track-dim` | `#1f2621` / `#56645a` | `#b9c4ba` / `#66736a` |
| Lit lamp `--lamp` + `--lamp-glow` | warm white `#fff4c9` | `#fff1bd` |
| Taken track `--taken` | amber `#d98f00` | `#ffb21f` |
| Signal aspects | `--sig-red #d6372e`, `--sig-yellow #f2b324`, `--sig-green #24a457` | same |
| Describer LED `--led` on `--led-bg` | `#ffb43a` on `#0f120f` | same |

Theme: follows `prefers-color-scheme`. The header button forces `data-theme` and saves the choice to localStorage.

## Type

- **Barlow Condensed** 600–700, uppercase, tracked `.1–.16em`: engraved plate labels, buttons, tabs, nameplate.
- **Barlow** 400–600: body copy and explanations.
- **JetBrains Mono**: patterns, test strings, state IDs, readouts. Use it only for code and data.
- **DotGothic16**: train-describer character cells only.

## Components

- **Plate input**: a black sunk field with plate ink and an LED-amber caret. Its border turns red on a fault.
- **Two-position switch** (`.mode-switch`) and **tab plates** (`.view-switch`): the selected plate is filled black.
- **Signal head**: three aspect lamps plus a black plate showing the result word and a one-line detail. It lies horizontal on phones.
- **Mimic**: Graphviz SVG restyled by CSS, on a dotted panel ground. `.lit` marks lamps, `.lit.accepting` turns green, `.edge.taken` is amber track, and `.edge.eps` is dashed dim track. Zoom is "auto": it fits unless that would shrink the drawing below 55%. A 1:1 toggle overrides it.
- **Berths**: fixed-size LED cells. `.read` cells are dimmed, `.current` is solid amber, and `.matched` gets a green underline (search mode).
- **Levers**: round raised buttons. The primary (run/pause) lever is filled black.
- **Fault**: a red "FAULT" tag, the message with a 1-based position, and a red triangle under the offending character. The previous diagram stays visible, dimmed and greyed (`.mimic.stale`).

## Motion

There is one authored moment. A lamp that has just lit "warms up" (a brightness and glow ramp over 420 ms with an expo ease-out). Run mode advances a step every 650 ms. Everything else is a short colour transition. `prefers-reduced-motion` turns transitions off.

## Rules

- No new colours outside the tokens. Red, yellow and green are reserved for signal meaning.
- The body background has faint 48px tile seams, standing in for the panel's tiles. Keep them faint.
- Icons are inline SVG symbols in `index.html` with filled 20px glyphs. Add new ones in the same style.
