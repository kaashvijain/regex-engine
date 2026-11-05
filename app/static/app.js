"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const els = {
    pattern: $("pattern"),
    patternWrap: $("pattern-wrap"),
    text: $("text"),
    fault: $("pattern-error"),
    faultCaret: $("fault-caret"),
    faultText: $("fault-text"),
    signal: $("signal"),
    signalWord: $("signal-word"),
    signalDetail: $("signal-detail"),
    mimic: $("mimic"),
    caption: $("panel-caption"),
    berths: $("berths"),
    readout: $("readout"),
    scrub: $("scrub"),
    play: $("btn-play"),
    prev: $("btn-prev"),
    next: $("btn-next"),
    reset: $("btn-reset"),
    end: $("btn-end"),
    statNfa: $("stat-nfa"),
    statDfa: $("stat-dfa"),
    statTok: $("stat-tok"),
    themeBtn: $("theme-btn"),
    shareBtn: $("share-btn"),
  };

  const state = {
    mode: "full",
    view: "nfa",
    data: null,      // last successful /api/analyze response
    step: 0,
    playing: null,   // interval id
    svgCache: {},    // view -> SVGElement for the current data
    reqId: 0,
  };

  /* ---------------- theme ---------------- */
  const storage = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  };
  function currentTheme() {
    const forced = document.documentElement.dataset.theme;
    if (forced) return forced;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function applyThemeButton() {
    const dark = currentTheme() === "dark";
    els.themeBtn.setAttribute("aria-label", dark ? "Switch to light panel" : "Switch to dark panel");
    els.themeBtn.title = els.themeBtn.getAttribute("aria-label");
    els.themeBtn.querySelector("use").setAttribute("href", dark ? "#i-sun" : "#i-moon");
  }
  const savedTheme = storage.get("signalbox-theme");
  if (savedTheme === "light" || savedTheme === "dark") document.documentElement.dataset.theme = savedTheme;
  applyThemeButton();
  els.themeBtn.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    storage.set("signalbox-theme", next);
    applyThemeButton();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyThemeButton);

  /* ---------------- URL state ---------------- */
  function readUrl() {
    const q = new URLSearchParams(location.search);
    if (q.has("p")) els.pattern.value = q.get("p");
    if (q.has("t")) els.text.value = q.get("t");
    if (q.get("m") === "search" || q.get("m") === "full") state.mode = q.get("m");
    if (["nfa", "dfa", "ast", "tokens"].includes(q.get("v"))) state.view = q.get("v");
  }
  function writeUrl() {
    const q = new URLSearchParams({ p: els.pattern.value, t: els.text.value, m: state.mode });
    if (state.view !== "nfa") q.set("v", state.view);
    history.replaceState(null, "", "?" + q.toString());
  }
  els.shareBtn.addEventListener("click", async () => {
    writeUrl();
    const label = els.shareBtn.querySelector("span");
    try {
      await navigator.clipboard.writeText(location.href);
      label.textContent = "Copied";
    } catch {
      label.textContent = "Link in address bar";
    }
    els.shareBtn.classList.add("copied");
    setTimeout(() => { label.textContent = "Copy link"; els.shareBtn.classList.remove("copied"); }, 1800);
  });

  /* ---------------- viz ---------------- */
  let vizPromise = null;
  function viz() {
    if (!vizPromise) {
      vizPromise = window.Viz
        ? window.Viz.instance()
        : Promise.reject(new Error("Graph renderer failed to load"));
    }
    return vizPromise;
  }

  async function renderDot(dot, view) {
    const v = await viz();
    const svg = v.renderSVGElement(dot);
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    const vb = svg.viewBox.baseVal;
    // Natural size, scaled up a touch; the panel scrolls when it's wider than the screen.
    const scale = view === "ast" ? 1.15 : 1.25;
    svg.style.width = Math.round(vb.width * scale) + "px";
    svg.classList.add(view);
    // Graphviz copies the DOT `class` attr onto <g>; drop titles so hover shows our tooltips only.
    svg.querySelectorAll("title").forEach((t) => {
      if (!t.parentNode.matches(".node[id^='dfa-']")) t.remove();
    });
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", {
      nfa: "NFA state diagram", dfa: "DFA state diagram", ast: "Parse tree",
    }[view]);
    return svg;
  }

  /* ---------------- analyze ---------------- */
  let debounce = null;
  function schedule() {
    clearTimeout(debounce);
    debounce = setTimeout(analyze, 180);
  }

  async function analyze() {
    const id = ++state.reqId;
    writeUrl();
    let res, body;
    try {
      res = await fetch("api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pattern: els.pattern.value, text: els.text.value, mode: state.mode }),
      });
      body = await res.json();
    } catch {
      if (id !== state.reqId) return;
      showFault("Can't reach the engine. Check your connection and try again.", null);
      return;
    }
    if (id !== state.reqId) return; // a newer request is in flight

    if (res.status === 400) {
      stop();
      showFault(body.error, body.position);
      setSignal("red", "Fault", "fix the pattern");
      if (state.data) {
        els.mimic.classList.add("stale");
        els.caption.textContent = "Showing the last valid pattern.";
      } else {
        els.mimic.replaceChildren(msg("Fix the pattern to draw the panel."));
      }
      return;
    }
    if (!res.ok) {
      const msg = res.status === 422 ? "Input too long: patterns up to 200 characters, strings up to 2000." : "The engine hit an unexpected error.";
      showFault(msg, null);
      return;
    }
    clearFault();
    stop();
    state.data = body;
    state.svgCache = {};
    state.step = body.trace.length - 1; // show the final state first
    els.scrub.max = String(body.trace.length - 1);
    els.statNfa.textContent = body.nfa.states;
    els.statDfa.textContent = body.dfa.states + (body.dfa.truncated ? "+" : "");
    els.statTok.textContent = body.tokens.filter((t) => t.type !== "CONCAT").length;
    updateSignal();
    await drawView();
    renderBerths();
    applyStep(false);
  }

  /* ---------------- faults ---------------- */
  function showFault(message, position) {
    els.fault.hidden = false;
    els.faultText.textContent = position == null ? message : `${message} — position ${position + 1}.`;
    els.patternWrap.classList.toggle("has-fault", position != null);
    if (position != null) {
      // Place a caret under the offending character.
      const input = els.pattern;
      const cs = getComputedStyle(input);
      const ctx = document.createElement("canvas").getContext("2d");
      ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      const before = ctx.measureText(input.value.slice(0, position)).width;
      const ch = ctx.measureText(input.value[position] || " ").width;
      const origin = els.fault.getBoundingClientRect().left;
      const left = input.getBoundingClientRect().left - origin
        + parseFloat(cs.paddingLeft) + before - input.scrollLeft + ch / 2;
      const mark = document.createElement("span");
      mark.className = "caret-mark";
      mark.style.left = Math.max(0, left) + "px";
      els.faultCaret.replaceChildren(mark);
    } else {
      els.faultCaret.replaceChildren();
    }
  }
  function clearFault() {
    els.fault.hidden = true;
    els.mimic.classList.remove("stale");
    els.patternWrap.classList.remove("has-fault");
  }

  /* ---------------- signal ---------------- */
  function setSignal(aspect, word, detail) {
    els.signal.dataset.aspect = aspect;
    els.signalWord.textContent = word;
    els.signalDetail.textContent = detail;
  }
  function updateSignal() {
    const d = state.data;
    if (d.mode === "full") {
      if (d.result.matched) setSignal("green", "Match", "whole string accepted");
      else setSignal("red", "No match", d.text.length ? "string rejected" : "empty string rejected");
    } else {
      const n = d.result.matches.length;
      const nonEmpty = d.result.matches.filter(([a, b]) => b > a).length;
      if (nonEmpty) setSignal("green", n === 1 ? "1 match" : `${n} matches`, "leftmost-longest");
      else if (n) setSignal("yellow", "Empty matches", "pattern accepts “”");
      else setSignal("red", "No match", "nothing found");
    }
  }

  /* ---------------- views ---------------- */
  const CAPTIONS = {
    nfa: (d) => `Thompson construction: ${d.nfa.states} states, ${d.nfa.edges.length} tracks.`
      + (d.mode === "search" ? " Search restarts at state " + d.nfa.start + " on every character." : ""),
    dfa: (d) => d.dfa.truncated
      ? `Subset construction stopped at ${d.dfa.states} states.`
      : `Subset construction, minimized: ${d.dfa.states} states. Hover a state for its NFA set.`,
    ast: () => "Recursive-descent parse. Chains of · and | are flattened.",
    tokens: () => "Tokenizer output. Dashed tokens are implicit concatenation.",
  };

  async function drawView() {
    const d = state.data;
    if (!d) return;
    els.caption.textContent = CAPTIONS[state.view](d);
    els.mimic.setAttribute("aria-labelledby", "tab-" + state.view);

    zoomBtn.hidden = state.view === "tokens";
    if (state.view === "tokens") {
      els.mimic.replaceChildren(tokenStrip(d.tokens));
      return;
    }
    let svg = state.svgCache[state.view];
    if (!svg) {
      const dot = state.view === "ast" ? d.ast.dot : d[state.view].dot;
      try {
        svg = await renderDot(dot, state.view);
      } catch (e) {
        els.mimic.replaceChildren(msg("The graph renderer didn't load. Reload the page to try again."));
        return;
      }
      state.svgCache[state.view] = svg;
    }
    if (d !== state.data) return; // superseded while rendering
    els.mimic.replaceChildren(svg);
    applyZoom();
    applyStep(false);
  }

  function msg(text) {
    const div = document.createElement("div");
    div.className = "mimic-msg";
    div.textContent = text;
    return div;
  }

  function tokenStrip(tokens) {
    const wrap = document.createElement("div");
    wrap.className = "token-strip";
    if (!tokens.length) wrap.append(msg("Empty pattern: no tokens. It matches only the empty string."));
    for (const t of tokens) {
      const el = document.createElement("div");
      el.className = "token" + (t.type === "CONCAT" ? " implicit" : "");
      const text = document.createElement("span");
      text.className = "token-text";
      text.textContent = t.type === "CONCAT" ? "·" : t.text;
      const type = document.createElement("span");
      type.className = "token-type";
      type.textContent = t.type === "CHARSET" ? (t.text.length > 1 ? "class" : "char") : t.type.toLowerCase();
      el.append(text, type);
      if (t.type !== "CONCAT") {
        const pos = document.createElement("span");
        pos.className = "token-pos";
        pos.textContent = "@" + t.pos;
        el.append(pos);
      }
      el.title = t.label ? `matches ${t.label}` : t.type;
      wrap.append(el);
    }
    return wrap;
  }

  document.querySelectorAll(".view-switch [role=tab]").forEach((tab) => {
    tab.addEventListener("click", () => selectView(tab.dataset.view));
    tab.addEventListener("keydown", (e) => {
      const tabs = [...document.querySelectorAll(".view-switch [role=tab]")];
      const i = tabs.indexOf(tab);
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
      if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
      if (j != null) { e.preventDefault(); tabs[j].focus(); selectView(tabs[j].dataset.view); }
    });
  });
  function selectView(view) {
    state.view = view;
    document.querySelectorAll(".view-switch [role=tab]").forEach((t) => {
      const on = t.dataset.view === view;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    writeUrl();
    drawView();
  }

  // Zoom: "auto" fits the panel unless that would shrink the drawing below
  // ~55%, in which case it shows full size and the panel scrolls.
  const zoomBtn = $("zoom-btn");
  let zoomChoice = "auto";
  function applyZoom() {
    const svg = els.mimic.querySelector("svg");
    let natural = zoomChoice === "natural";
    if (zoomChoice === "auto" && svg) {
      const avail = els.mimic.clientWidth - 40;
      natural = avail / parseFloat(svg.style.width) < 0.55;
    }
    els.mimic.classList.toggle("natural", natural);
    zoomBtn.setAttribute("aria-pressed", String(natural));
    zoomBtn.title = natural ? "Fit the diagram to the panel" : "Show the diagram at full size";
  }
  zoomBtn.addEventListener("click", () => {
    zoomChoice = els.mimic.classList.contains("natural") ? "fit" : "natural";
    applyZoom();
  });
  addEventListener("resize", () => { if (zoomChoice === "auto") applyZoom(); });

  /* ---------------- describer (input tape) ---------------- */
  function renderBerths() {
    const d = state.data;
    els.berths.replaceChildren();
    if (!d.text.length) {
      const note = document.createElement("span");
      note.className = "berth empty-note";
      note.textContent = "empty string";
      els.berths.append(note);
      return;
    }
    const matched = new Uint8Array(d.text.length);
    if (d.mode === "search") {
      for (const [a, b] of d.result.matches) for (let i = a; i < b; i++) matched[i] = 1;
    }
    [...d.text].forEach((ch, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "berth" + (matched[i] ? " matched" : "") + (ch === " " ? " space" : "");
      b.textContent = ch === " " ? "" : ch;
      b.setAttribute("aria-label", `Step to character ${i + 1}: ${ch === " " ? "space" : ch}`);
      b.tabIndex = -1;
      b.addEventListener("click", () => { stop(); state.step = i + 1; applyStep(true); });
      els.berths.append(b);
    });
  }

  function applyStep(animate) {
    const d = state.data;
    if (!d) return;
    const steps = d.trace;
    const s = steps[state.step];
    els.scrub.value = String(state.step);

    // berths
    const cells = els.berths.querySelectorAll(".berth:not(.empty-note)");
    cells.forEach((c, i) => {
      c.classList.toggle("read", i < state.step - 1);
      c.classList.toggle("current", i === state.step - 1);
    });
    const cur = cells[state.step - 1];
    if (cur && animate) cur.scrollIntoView({ block: "nearest", inline: "nearest" });

    // readout
    const read = s.char == null ? "start" : `read ${JSON.stringify(s.char)}`;
    let where;
    if (state.view === "dfa") {
      if (d.mode === "search") where = "DFA trace runs in full-match mode";
      else where = s.dfa == null ? "DFA: dead state, can't match" : `DFA state ${s.dfa}`;
    } else {
      where = s.states.length ? `lit {${s.states.join(", ")}}` : "no states lit, can't match";
      if (d.mode === "search" && s.accepting) where += " · a match ends here";
    }
    els.readout.textContent = `step ${state.step}/${steps.length - 1} · ${read} · ${where}`;

    // levers
    els.prev.disabled = els.reset.disabled = state.step === 0;
    els.next.disabled = els.end.disabled = state.step === steps.length - 1;
    els.play.disabled = steps.length < 2;

    // lamps
    const svg = els.mimic.querySelector("svg");
    if (!svg) return;
    if (svg.classList.contains("nfa")) {
      const lit = new Set(s.states);
      svg.querySelectorAll(".node[id^='nfa-']").forEach((n) => {
        const id = Number(n.id.slice(4));
        const on = lit.has(id);
        const wasOn = n.classList.contains("lit");
        n.classList.toggle("lit", on);
        n.classList.toggle("accepting", on && id === d.nfa.accept);
        n.classList.toggle("flash", animate && on && !wasOn);
      });
      const taken = new Set(s.taken);
      svg.querySelectorAll(".edge[id^='nfa-e']").forEach((e) => {
        e.classList.toggle("taken", taken.has(Number(e.id.slice(5))));
      });
    } else if (svg.classList.contains("dfa")) {
      const acc = new Set(d.dfa.accepting);
      svg.querySelectorAll(".node[id^='dfa-']").forEach((n) => {
        const id = Number(n.id.slice(4));
        const on = id === s.dfa;
        const wasOn = n.classList.contains("lit");
        n.classList.toggle("lit", on);
        n.classList.toggle("accepting", on && acc.has(id));
        n.classList.toggle("flash", animate && on && !wasOn);
      });
    }
  }

  function go(step) {
    const last = state.data ? state.data.trace.length - 1 : 0;
    state.step = Math.max(0, Math.min(last, step));
    applyStep(true);
  }
  function stop() {
    if (state.playing) clearInterval(state.playing);
    state.playing = null;
    els.play.querySelector("use").setAttribute("href", "#i-play");
    els.play.setAttribute("aria-label", "Run");
  }
  function play() {
    if (!state.data) return;
    if (state.playing) return stop();
    const last = state.data.trace.length - 1;
    if (state.step >= last) go(0);
    els.play.querySelector("use").setAttribute("href", "#i-pause");
    els.play.setAttribute("aria-label", "Pause");
    const delay = matchMedia("(prefers-reduced-motion: reduce)").matches ? 900 : 650;
    state.playing = setInterval(() => {
      if (state.step >= last) return stop();
      go(state.step + 1);
    }, delay);
  }

  els.play.addEventListener("click", play);
  els.prev.addEventListener("click", () => { stop(); go(state.step - 1); });
  els.next.addEventListener("click", () => { stop(); go(state.step + 1); });
  els.reset.addEventListener("click", () => { stop(); go(0); });
  els.end.addEventListener("click", () => { stop(); go(Infinity); });
  els.scrub.addEventListener("input", () => { stop(); go(Number(els.scrub.value)); });

  document.addEventListener("keydown", (e) => {
    const t = e.target;
    if (t.matches("input[type=text], textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    if (t.matches("[role=tab]") && (e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
    const map = {
      ArrowLeft: () => { stop(); go(state.step - 1); },
      ArrowRight: () => { stop(); go(state.step + 1); },
      Home: () => { stop(); go(0); },
      End: () => { stop(); go(Infinity); },
      " ": () => { if (!t.matches("button, input, summary, a")) play(); else return false; },
    };
    if (map[e.key] && map[e.key]() !== false) e.preventDefault();
  });

  /* ---------------- inputs ---------------- */
  els.pattern.addEventListener("input", schedule);
  els.text.addEventListener("input", schedule);

  function setMode(mode) {
    state.mode = mode;
    document.querySelectorAll(".mode-switch [role=radio]").forEach((b) => {
      const on = b.dataset.mode === mode;
      b.setAttribute("aria-checked", String(on));
      b.tabIndex = on ? 0 : -1;
    });
  }
  document.querySelectorAll(".mode-switch [role=radio]").forEach((b) => {
    b.addEventListener("click", () => { setMode(b.dataset.mode); analyze(); });
    b.addEventListener("keydown", (e) => {
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) {
        e.preventDefault();
        const next = state.mode === "full" ? "search" : "full";
        setMode(next);
        document.querySelector(`.mode-switch [data-mode=${next}]`).focus();
        analyze();
      }
    });
  });

  document.querySelectorAll(".preset").forEach((p) => {
    p.addEventListener("click", () => {
      els.pattern.value = p.dataset.p;
      els.text.value = p.dataset.t;
      setMode(p.dataset.m);
      analyze();
    });
  });

  /* ---------------- boot ---------------- */
  readUrl();
  setMode(state.mode);
  selectView(state.view);
  analyze();
})();
