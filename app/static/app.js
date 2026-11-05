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
    describerLabel: $("describer-label"),
    berths: $("berths"),
    readout: $("readout"),
    scrub: $("scrub"),
    play: $("btn-play"),
    prev: $("btn-prev"),
    next: $("btn-next"),
    first: $("btn-reset"),
    last: $("btn-end"),
    themeBtn: $("theme-btn"),
    zoomBtn: $("zoom-btn"),
  };

  const state = {
    mode: "full",
    view: "nfa",
    data: null,      // last successful /api/analyze response
    step: 0,         // simulation step (NFA / DFA / tokens views)
    astStep: 0,      // parse-tree build step
    playing: null,   // interval id
    svgCache: {},    // view -> SVGElement for the current data
    reqId: 0,
    zoom: "auto",
  };

  const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

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
    const label = dark ? "Switch to light theme" : "Switch to dark theme";
    els.themeBtn.setAttribute("aria-label", label);
    els.themeBtn.title = label;
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

  /* ---------------- URL state (the address bar is the share link) ---------------- */
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
    const scale = view === "ast" ? 1.2 : 1.25;
    svg.style.width = Math.round(vb.width * scale) + "px";
    svg.classList.add(view);
    svg.querySelectorAll("title").forEach((t) => {
      if (!t.parentNode.matches(".node[id^='dfa-']")) t.remove();
    });
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", { nfa: "NFA state diagram", dfa: "DFA state diagram", ast: "Parse tree" }[view]);
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
      setVerdict("red", "Invalid", "fix the pattern");
      if (state.data) {
        els.mimic.classList.add("stale");
        els.caption.textContent = "Showing the last valid pattern.";
      } else {
        els.mimic.replaceChildren(msg("Fix the pattern to draw the diagram."));
      }
      return;
    }
    if (!res.ok) {
      const m = res.status === 422 ? "Input too long: patterns up to 200 characters, strings up to 2000." : "The engine hit an unexpected error.";
      showFault(m, null);
      return;
    }
    const patternChanged = !state.data || state.data.pattern !== body.pattern;
    clearFault();
    stop();
    state.data = body;
    state.svgCache = {};
    state.step = body.trace.length - 1; // show the final state first
    state.astStep = body.ast.build.length;
    updateVerdict();
    await drawView();
    // Parse tree: replay the build whenever the pattern changes.
    if (state.view === "ast" && patternChanged) replayBuild();
  }

  /* ---------------- faults ---------------- */
  function showFault(message, position) {
    els.fault.hidden = false;
    els.faultText.textContent = position == null ? message : `${message} (character ${position + 1})`;
    els.patternWrap.classList.toggle("has-fault", position != null);
    els.faultCaret.replaceChildren();
    if (position == null) return;
    const input = els.pattern;
    const cs = getComputedStyle(input);
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const before = ctx.measureText(input.value.slice(0, position)).width;
    const ch = ctx.measureText(input.value[position] || " ").width;
    const left = input.getBoundingClientRect().left - els.fault.getBoundingClientRect().left
      + parseFloat(cs.paddingLeft) + before - input.scrollLeft + ch / 2;
    const mark = document.createElement("span");
    mark.className = "caret-mark";
    mark.style.left = Math.max(0, left) + "px";
    els.faultCaret.append(mark);
  }
  function clearFault() {
    els.fault.hidden = true;
    els.patternWrap.classList.remove("has-fault");
    els.mimic.classList.remove("stale");
  }

  /* ---------------- verdict ---------------- */
  function setVerdict(aspect, word, detail) {
    els.signal.dataset.aspect = aspect;
    els.signalWord.textContent = word;
    els.signalDetail.textContent = detail;
  }
  function updateVerdict() {
    const d = state.data;
    if (d.mode === "full") {
      if (d.result.matched) setVerdict("green", "Match", "whole string accepted");
      else setVerdict("red", "No match", d.text.length ? "string rejected" : "empty string rejected");
    } else {
      const n = d.result.matches.length;
      const nonEmpty = d.result.matches.filter(([a, b]) => b > a).length;
      if (nonEmpty) setVerdict("green", n === 1 ? "1 match" : `${n} matches`, "leftmost-longest");
      else if (n) setVerdict("yellow", "Empty", "only empty matches");
      else setVerdict("red", "No match", "nothing found");
    }
  }

  /* ---------------- views ---------------- */
  const CAPTIONS = {
    nfa: (d) => `Thompson construction · ${d.nfa.states} states · ${d.nfa.edges.length} transitions`
      + (d.mode === "search" ? ` · search restarts at state ${d.nfa.start} on every character` : ""),
    dfa: (d) => d.dfa.truncated
      ? `Subset construction stopped at ${d.dfa.states} states`
      : `Subset construction, minimized · ${d.dfa.states} states · hover a state for its NFA set`,
    ast: (d) => `Recursive-descent parse · ${d.ast.build.length} nodes, built bottom-up`,
    tokens: (d) => `Tokenizer · ${d.tokens.filter((t) => t.type !== "CONCAT").length} tokens; dashed ones are implicit concatenation`,
  };

  async function drawView() {
    const d = state.data;
    if (!d) return;
    els.caption.textContent = CAPTIONS[state.view](d);
    els.mimic.setAttribute("aria-labelledby", "tab-" + state.view);
    els.describerLabel.textContent = state.view === "ast" ? "Pattern, as the parser reads it" : "Input";
    renderBerths();
    els.zoomBtn.hidden = state.view === "tokens";

    if (state.view === "tokens") {
      els.mimic.replaceChildren(tokenStrip(d.tokens));
      applyStep(false);
      return;
    }
    let svg = state.svgCache[state.view];
    if (!svg) {
      const dot = d[state.view].dot;
      try {
        svg = await renderDot(dot, state.view);
      } catch {
        els.mimic.replaceChildren(msg("The graph renderer didn't load. Reload the page to try again."));
        return;
      }
      if (d !== state.data) return; // superseded while rendering
      state.svgCache[state.view] = svg;
    }
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

  const tabs = [...document.querySelectorAll(".tabs [role=tab]")];
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => selectView(tab.dataset.view));
    tab.addEventListener("keydown", (e) => {
      const i = tabs.indexOf(tab);
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
      if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
      if (j != null) { e.preventDefault(); tabs[j].focus(); selectView(tabs[j].dataset.view); }
    });
  });
  async function selectView(view, { replay = true } = {}) {
    const changed = view !== state.view;
    stop();
    state.view = view;
    tabs.forEach((t) => {
      const on = t.dataset.view === view;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    writeUrl();
    await drawView();
    if (view === "ast" && changed && replay) replayBuild();
  }

  /* ---------------- zoom ---------------- */
  // "auto" fits the panel unless that would shrink the drawing below ~55%.
  function applyZoom() {
    const svg = els.mimic.querySelector("svg");
    let natural = state.zoom === "natural";
    if (state.zoom === "auto" && svg) {
      natural = (els.mimic.clientWidth - 48) / parseFloat(svg.style.width) < 0.55;
    }
    els.mimic.classList.toggle("natural", natural);
    els.zoomBtn.setAttribute("aria-pressed", String(natural));
    els.zoomBtn.title = natural ? "Fit the diagram to the panel" : "Show the diagram at full size";
  }
  els.zoomBtn.addEventListener("click", () => {
    state.zoom = els.mimic.classList.contains("natural") ? "fit" : "natural";
    applyZoom();
  });
  addEventListener("resize", () => { if (state.zoom === "auto") applyZoom(); });

  /* ---------------- timeline: simulation steps or parse-tree build steps ---------------- */
  const isBuild = () => state.view === "ast";
  const lastStep = () => !state.data ? 0 : isBuild() ? state.data.ast.build.length : state.data.trace.length - 1;
  const getStep = () => (isBuild() ? state.astStep : state.step);
  function setStep(n) {
    if (isBuild()) state.astStep = n; else state.step = n;
  }

  function renderBerths() {
    const d = state.data;
    els.berths.replaceChildren();
    const source = isBuild() ? d.pattern : d.text;
    if (!source.length) {
      const note = document.createElement("span");
      note.className = "berth empty-note";
      note.textContent = isBuild() ? "empty pattern" : "empty string";
      els.berths.append(note);
      return;
    }
    const matched = new Uint8Array(source.length);
    if (!isBuild() && d.mode === "search") {
      for (const [a, b] of d.result.matches) for (let i = a; i < b; i++) matched[i] = 1;
    }
    [...source].forEach((ch, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "berth" + (matched[i] ? " matched" : "") + (ch === " " ? " space" : "");
      b.textContent = ch === " " ? "" : ch;
      b.tabIndex = -1;
      if (isBuild()) {
        b.setAttribute("aria-label", `Character ${i + 1}: ${ch === " " ? "space" : ch}`);
        b.addEventListener("click", () => {
          // jump to the step that first builds a node starting here
          const k = d.ast.build.findIndex((n) => n.span[0] <= i && i < n.span[1]);
          if (k >= 0) { stop(); go(k + 1); }
        });
      } else {
        b.setAttribute("aria-label", `Step to character ${i + 1}: ${ch === " " ? "space" : ch}`);
        b.addEventListener("click", () => { stop(); go(i + 1); });
      }
      els.berths.append(b);
    });
  }

  function applyStep(animate) {
    const d = state.data;
    if (!d) return;
    const step = getStep();
    const last = lastStep();
    els.scrub.max = String(last);
    els.scrub.value = String(step);
    els.prev.disabled = els.first.disabled = step === 0;
    els.next.disabled = els.last.disabled = step === last;
    els.play.disabled = last < 1;
    if (isBuild()) applyBuildStep(step, animate);
    else applyTraceStep(step, animate);
  }

  function applyTraceStep(step, animate) {
    const d = state.data;
    const s = d.trace[step];
    const cells = els.berths.querySelectorAll(".berth:not(.empty-note)");
    cells.forEach((c, i) => {
      c.classList.remove("span");
      c.classList.toggle("read", i < step - 1);
      c.classList.toggle("current", i === step - 1);
    });
    if (animate && cells[step - 1]) cells[step - 1].scrollIntoView({ block: "nearest", inline: "nearest" });

    const read = s.char == null ? "start" : `read ${JSON.stringify(s.char)}`;
    let where;
    if (state.view === "dfa") {
      if (d.mode === "search") where = "DFA trace runs in full-match mode";
      else where = s.dfa == null ? "dead state, can't match" : `DFA state ${s.dfa}`;
    } else {
      where = s.states.length ? `active {${s.states.join(", ")}}` : "no active states, can't match";
      if (d.mode === "search" && s.accepting) where += " · a match ends here";
    }
    els.readout.textContent = `step ${step}/${d.trace.length - 1} · ${read} · ${where}`;

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

  function applyBuildStep(step, animate) {
    const d = state.data;
    const build = d.ast.build;
    const built = new Set(build.slice(0, step).map((b) => b.node));
    const fresh = step > 0 ? build[step - 1] : null;

    const svg = els.mimic.querySelector("svg.ast");
    if (svg) {
      svg.querySelectorAll(".node[id^='ast-']").forEach((n) => {
        const id = Number(n.id.slice(4));
        n.classList.toggle("pending", !built.has(id));
        const isFresh = fresh && fresh.node === id;
        n.classList.toggle("fresh", !!isFresh);
        if (isFresh && animate) { n.style.animation = "none"; void n.getBBox(); n.style.animation = ""; }
      });
      for (const b of build) {
        const e = svg.querySelector(`#ast-e${b.node}`);
        if (e) e.classList.toggle("pending", !(built.has(b.node) && built.has(b.parent)));
      }
    }

    const cells = els.berths.querySelectorAll(".berth:not(.empty-note)");
    cells.forEach((c, i) => {
      c.classList.remove("read", "current");
      c.classList.toggle("span", !!fresh && fresh.span[0] <= i && i < fresh.span[1]);
    });

    if (!fresh) {
      els.readout.textContent = `step 0/${build.length} · nothing built yet`;
    } else {
      const src = d.pattern.slice(fresh.span[0], fresh.span[1]);
      const what = fresh.kind === "char" ? `char ${fresh.label}` : fresh.kind === "empty" ? "empty (ε)" : fresh.kind;
      const from = src ? ` from ${JSON.stringify(src)}` : "";
      els.readout.textContent = `step ${step}/${build.length} · built ${what}${from}`;
    }
  }

  function go(step) {
    setStep(Math.max(0, Math.min(lastStep(), step)));
    applyStep(true);
  }
  function stop() {
    if (state.playing) clearInterval(state.playing);
    state.playing = null;
    els.play.querySelector("use").setAttribute("href", "#i-play");
    els.play.setAttribute("aria-label", "Play");
  }
  function play() {
    if (!state.data) return;
    if (state.playing) return stop();
    if (getStep() >= lastStep()) go(0);
    els.play.querySelector("use").setAttribute("href", "#i-pause");
    els.play.setAttribute("aria-label", "Pause");
    const delay = isBuild() ? 420 : 650;
    state.playing = setInterval(() => {
      if (getStep() >= lastStep()) return stop();
      go(getStep() + 1);
    }, reducedMotion() ? delay * 1.4 : delay);
  }
  function replayBuild() {
    if (reducedMotion()) return; // leave the finished tree on screen
    stop();
    go(0);
    play();
  }

  els.play.addEventListener("click", play);
  els.prev.addEventListener("click", () => { stop(); go(getStep() - 1); });
  els.next.addEventListener("click", () => { stop(); go(getStep() + 1); });
  els.first.addEventListener("click", () => { stop(); go(0); });
  els.last.addEventListener("click", () => { stop(); go(Infinity); });
  els.scrub.addEventListener("input", () => { stop(); go(Number(els.scrub.value)); });

  document.addEventListener("keydown", (e) => {
    const t = e.target;
    if (t.matches("input[type=text], textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    if (t.matches("[role=tab]") && (e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
    const map = {
      ArrowLeft: () => { stop(); go(getStep() - 1); },
      ArrowRight: () => { stop(); go(getStep() + 1); },
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
    document.querySelectorAll(".segmented [role=radio]").forEach((b) => {
      const on = b.dataset.mode === mode;
      b.setAttribute("aria-checked", String(on));
      b.tabIndex = on ? 0 : -1;
    });
  }
  document.querySelectorAll(".segmented [role=radio]").forEach((b) => {
    b.addEventListener("click", () => { setMode(b.dataset.mode); analyze(); });
    b.addEventListener("keydown", (e) => {
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) {
        e.preventDefault();
        const next = state.mode === "full" ? "search" : "full";
        setMode(next);
        document.querySelector(`.segmented [data-mode=${next}]`).focus();
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

  // close the syntax popover on outside click / Escape
  const syntax = document.querySelector(".syntax");
  document.addEventListener("click", (e) => { if (syntax.open && !syntax.contains(e.target)) syntax.open = false; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && syntax.open) { syntax.open = false; syntax.querySelector("summary").focus(); } });

  /* ---------------- boot ---------------- */
  readUrl();
  setMode(state.mode);
  tabs.forEach((t) => {
    const on = t.dataset.view === state.view;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
  });
  analyze();
})();
