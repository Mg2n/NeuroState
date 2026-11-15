// The interactive demo: one fixed public recording, every view from the same precomputed run (app/cache/demo).
// Each step is one idea on one screen: a title, one line to say aloud, and a main visual that fills the screen.
// Formulas and detail open in the "How it works" drawer, for questions.
import { howTo } from "./howto.js";
import { buildPairs, drawTransitions, mountExplorer } from "./results.js";
import { SignalView } from "./signal.js";
import { api, f, h, plotBase, plotConfig, stateColor, stateScale, STATES, T } from "./util.js";

const ns = (window.__ns = window.__ns || {});
const PCT = (x, d = 1) => `${f(x, d)}%`;
const N = (x) => Number(x).toLocaleString("en-US");

const STAGES = [
  { id: "recording", short: "Recording", title: "The recording", step: "read" },
  { id: "prepare", short: "Preprocess", title: "Clean the signal", step: "prepare" },
  { id: "snapshots", short: "Snapshots", title: "Each instant is a scalp map", step: "snapshots", isNew: true },
  { id: "peaks", short: "GFP peaks", title: "Keep the clearest moments", step: "peaks" },
  { id: "fit", short: "Patterns", title: "Recurring patterns become four maps", step: "fit" },
  { id: "name", short: "Names A–D", title: "Name the maps against published maps", step: "name" },
  { id: "timeline", short: "Labels", title: "Every moment labelled", step: "label" },
  { id: "measures", short: "Measures", title: "How long, how often, how much", step: "measures" },
  { id: "transitions", short: "Transitions", title: "Which map comes next", step: "transitions", isNew: true },
  { id: "cnn", short: "CNN input", title: "The timeline becomes CNN input", step: "cnn" },
];
const STEP_RESULT = { snapshots: "prepare", transitions: "measures" };

let RUN = null;
let current = 0;
let pick = 1; // map chosen on the measures / transitions steps (B: the label of the example moment)

function lede(id, run) {
  const s = run.steps;
  return {
    recording: `An EEG file stores voltages from electrodes on the scalp, sampled many times per second. NeuroState uses the <b>19 standard electrodes</b>.`,
    prepare: `Each electrode is measured against the average of all 19, then filtered to <b>2–20 Hz</b> and resampled to <b>128 samples per second</b>.`,
    snapshots: `Freeze one instant: the 19 voltages at that moment, drawn on the head, form a <b>scalp map</b>. Click the traces to pick another instant.`,
    peaks: `The field’s strength (GFP) rises and falls. At its <b>peaks</b> the map is strongest and clearest, so the ${N(s.peaks.n_used)} peaks are used to find the patterns.`,
    fit: `The ${N(s.fit.n_peaks)} peak maps are grouped by shape, ignoring polarity. Each group’s typical shape becomes one of <b>four maps</b>.`,
    name: `Each map is paired with its closest published reference map (Koenig et al. 2002) and takes its name. <b>|r| = 1</b> means an identical shape.`,
    timeline: `Every one of the ${N(s.label.n_samples)} samples takes the label of the fitted map it matches best. Click any moment to see why it got its label, or press “Show an example”.`,
    measures: `Pick a map. Its visits along the timeline give three numbers: <b>duration</b>, <b>occurrence</b> and <b>coverage</b>.`,
    transitions: `Every switch from one map to another is counted. For each map: <b>where does the timeline go next?</b>`,
    cnn: `The timeline is cut into <b>4-second windows</b>. Each becomes four rows of 0s and 1s, one per map: the input the sequence CNN reads.`,
  }[id];
}

export async function renderDemo(view, { stage = null } = {}) {
  view.innerHTML = "";
  try {
    RUN = RUN || (await api("/api/demo"));
  } catch (e) {
    view.append(h("div", { class: "notice error" }, h("b", {}, "The demo bundle is not built yet."), h("br"),
      "Run once: experiments/.venv/bin/python app/tools/fetch_public_inputs.py (downloads and verifies the public sample, then builds the bundle)."));
    return;
  }
  ns.demo = RUN;
  const nav = h("nav", { class: "stages", id: "stages" });
  const exampleBtn = h("button", { class: "btn btn-primary", type: "button", id: "show-example" }, "Show an example");
  const body = h("div", { class: "stage-body", id: "stage-body" });
  view.append(h("div", { class: "demo-bar" }, h("span", { class: "demo-tag" }, "Demo · S001R02"), nav, exampleBtn), body);
  STAGES.forEach((st, k) => nav.append(h("button", { type: "button", class: `stage-pill${st.isNew ? " new" : ""}`, "data-stage": st.id, title: st.title, onclick: () => go(k) },
    h("span", { class: "n" }, k + 1), st.short)));
  exampleBtn.onclick = () => showExample();
  const drawer = ensureDrawer();

  async function go(k, opts = {}) {
    current = Math.max(0, Math.min(STAGES.length - 1, k));
    const st = STAGES[current];
    drawer.close();
    nav.querySelectorAll(".stage-pill").forEach((b, i) => { b.classList.toggle("active", i === current); b.classList.toggle("seen", i < current); });
    ns.stage = st.id;
    ns.stageReady = null;
    body.innerHTML = "";
    body.classList.remove("enter"); void body.offsetWidth; body.classList.add("enter");
    const prev = h("button", { class: "btn btn-ghost", type: "button", id: "stage-prev", disabled: current === 0, onclick: () => go(current - 1), "aria-label": "previous step" }, "←");
    const next = h("button", { class: "btn", type: "button", id: "stage-next", disabled: current === STAGES.length - 1, onclick: () => go(current + 1) },
      current === STAGES.length - 1 ? "End" : `${STAGES[current + 1].short} →`);
    const how = h("button", { class: "btn btn-ghost how-btn", type: "button", id: "how-btn", onclick: () => drawer.open(st, RUN) }, "How it works");
    const canvas = h("div", { class: "canvas", id: "canvas" });
    const stageEl = h("div", { class: "stage", "data-stage": st.id },
      h("div", { class: "stage-head" },
        h("div", { class: "t" }, h("div", { class: "k" }, `Step ${current + 1} of ${STAGES.length}`), h("h2", {}, st.title), h("p", { class: "lede", html: lede(st.id, RUN) })),
        h("div", { class: "stage-nav" }, how, prev, next)),
      canvas);
    body.append(stageEl);
    fitCanvas(stageEl, canvas);
    await RENDER[st.id](canvas, RUN, opts, stageEl);
    // plots measured their box before the text around them settled: fit them to it now
    await Promise.all([...canvas.querySelectorAll(".js-plotly-plot")].map((p) => Plotly.Plots.resize(p)));
    ns.stageReady = st.id;
  }
  ns.goStage = go;

  async function showExample() {
    const i = RUN.example_i;
    if (STAGES[current].id !== "timeline") await go(STAGES.findIndex((x) => x.id === "timeline"), { exampleI: i });
    else await ns.setCursor(i, { span: 4 });
    const insp = document.getElementById("inspector");
    insp.classList.remove("flash"); void insp.offsetWidth; insp.classList.add("flash");
    ns.exampleShown = i;
  }
  ns.showExample = showExample;

  const onKey = (e) => {
    if (!document.body.contains(nav)) { document.removeEventListener("keydown", onKey); return; }
    if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "Escape") drawer.close();
    else if (/^[0-9]$/.test(e.key)) go(e.key === "0" ? 9 : Number(e.key) - 1);
    else if (e.key === "ArrowRight") go(current + 1);
    else if (e.key === "ArrowLeft") go(current - 1);
  };
  document.addEventListener("keydown", onKey);
  let rt = null;
  const onResize = () => {
    if (!document.body.contains(nav)) { window.removeEventListener("resize", onResize); return; }
    clearTimeout(rt);
    rt = setTimeout(() => {
      const stageEl = body.querySelector(".stage"), canvas = body.querySelector("#canvas");
      if (stageEl && canvas) fitCanvas(stageEl, canvas);
      body.querySelectorAll(".js-plotly-plot").forEach((p) => Plotly.Plots.resize(p));
    }, 120);
  };
  window.addEventListener("resize", onResize);
  await go(stage !== null ? stage : 0);
}

// the canvas takes all the height left on screen (the main visual is never below the fold)
function fitCanvas(stageEl, canvas) {
  const top = canvas.getBoundingClientRect().top + window.scrollY;
  const hgt = Math.max(380, Math.floor(window.innerHeight - top - 14));
  canvas.style.height = `${hgt}px`;
  canvas.style.setProperty("--canvas-h", `${hgt}px`);
  stageEl.classList.toggle("compact", hgt < 600);
}

function ensureDrawer() {
  let el = document.getElementById("how-drawer");
  if (!el) {
    el = h("aside", { class: "drawer", id: "how-drawer", "aria-hidden": "true" });
    document.body.append(el);
  }
  return {
    open(st, run) {
      el.innerHTML = "";
      const close = h("button", { class: "btn btn-ghost btn-small drawer-close", type: "button", onclick: () => this.close() }, "Close ✕");
      el.append(close, h("div", { class: "k kicker" }, "How it works"), h("h3", {}, st.title), howTo(st.step, run.steps[STEP_RESULT[st.id] || st.step]));
      el.classList.add("open");
      el.setAttribute("aria-hidden", "false");
      ns.drawerOpen = true;
    },
    close() { el.classList.remove("open"); el.setAttribute("aria-hidden", "true"); ns.drawerOpen = false; },
  };
}

const big = (n, l, s) => h("div", { class: "big" }, h("span", { class: "n" }, n), h("span", { class: "l" }, l), s ? h("span", { class: "s" }, s) : null);
const panel = (...kids) => h("section", { class: "panel" }, ...kids);
const cap = (html) => h("p", { class: "cap", html });
const font14 = (extra = {}) => plotBase({ font: { family: `${T.fonts.sans}, sans-serif`, color: T.text.muted, size: 14 }, ...extra });
const instantPng = (run, i, vmax) => `/api/runs/${run.run_id}/instant.png?i=${i}${vmax ? `&vmax=${vmax}` : ""}`;
const niceMax = (v) => Math.ceil(v / 5) * 5;

// 10-20 electrode positions, schematic (head of radius 1, nose up)
const POS = { Fp1: [-0.3, -0.88], Fp2: [0.3, -0.88], F7: [-0.73, -0.53], F3: [-0.38, -0.47], Fz: [0, -0.45], F4: [0.38, -0.47], F8: [0.73, -0.53],
  T3: [-0.9, 0], C3: [-0.45, 0], Cz: [0, 0], C4: [0.45, 0], T4: [0.9, 0], T5: [-0.73, 0.53], P3: [-0.38, 0.47], Pz: [0, 0.45], P4: [0.38, 0.47],
  T6: [0.73, 0.53], O1: [-0.3, 0.88], O2: [0.3, 0.88] };

function headSvg(shown) {
  const cx = 130, cy = 128, R = 100, NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 260 250");
  svg.setAttribute("class", "head-svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "The 19 electrodes used, on a schematic head");
  const el = (tag, attrs, text) => { const e = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v)); if (text) e.textContent = text; svg.append(e); return e; };
  el("path", { d: `M${cx - 14} ${cy - R + 3} L${cx} ${cy - R - 16} L${cx + 14} ${cy - R + 3}`, fill: "none", stroke: T.text.muted, "stroke-width": 2 });
  el("ellipse", { cx: cx - R - 4, cy, rx: 7, ry: 20, fill: "none", stroke: T.text.muted, "stroke-width": 2 });
  el("ellipse", { cx: cx + R + 4, cy, rx: 7, ry: 20, fill: "none", stroke: T.text.muted, "stroke-width": 2 });
  el("circle", { cx, cy, r: R, fill: T.surface.inset, stroke: T.text.muted, "stroke-width": 2 });
  for (const [name, [x, y]] of Object.entries(POS)) {
    const on = shown.includes(name);
    el("circle", { cx: cx + x * R * 0.98, cy: cy + y * R * 0.98, r: 14, fill: on ? T.gold : T.surface.raised, stroke: on ? T.gold : T.text.dim, "stroke-width": 1.5 });
    el("text", { x: cx + x * R * 0.98, y: cy + y * R * 0.98 + 4, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700, fill: on ? T.text.onGold : T.text.primary, "font-family": T.fonts.sans }, name);
  }
  el("text", { x: cx, y: 246, "text-anchor": "middle", "font-size": 12, fill: T.text.muted, "font-family": T.fonts.sans }, "nose up · gold = the 8 traces drawn");
  return svg;
}

// ------------------------------------------------------------------------------------------------ the steps
const RENDER = {
  async recording(canvas, run) {
    const r = run.steps.read, sg = run.steps.segment;
    const wave = h("div", { class: "plot-fill", id: "wave" });
    canvas.append(
      panel(cap(`<b>As recorded</b>: original reference, ${f(r.sfreq, 0)} samples per second, µV · ${run.default_view.length} of the 19 electrodes drawn`), wave),
      h("aside", { class: "panel side" }, headSvg(run.default_view),
        big(`${r.n_channels} → 19`, "electrodes in the file → standard electrodes used", Object.entries(r.aliases_applied).length ? "T7, T8, P7, P8 are read as T3, T4, T5, T6" : null),
        big(`${f(r.sfreq, 0)} /s`, "voltage samples per second, per electrode"),
        big(`${f(sg.duration_s, 0)} s`, "eyes-closed rest, analysed in full", sg.method === "full" ? "no “eyes closed” marker in this file, so all of it is used" : sg.how)));
    const v = new SignalView(wave, run, { view: "raw", timeline: false, initialSpan: 5 });
    await v.init();
  },

  async prepare(canvas, run) {
    const p = run.steps.prepare;
    const wave = h("div", { class: "plot-fill", id: "wave" });
    const raw = h("button", { type: "button", "aria-pressed": "false", id: "view-raw" }, "Before");
    const proc = h("button", { type: "button", "aria-pressed": "true", id: "view-proc" }, "After");
    const note = h("span", { class: "cap", style: { margin: 0 } });
    canvas.append(
      panel(h("div", { class: "toolbar" }, h("div", { class: "seg" }, raw, proc), note), wave),
      h("aside", { class: "panel side" },
        big("1", "Re-reference", "each electrode minus the average of all 19 at that instant"),
        big("2", "Band-pass 2–20 Hz", "keeps the rhythms the published maps were made from; removes slow drift and fast noise"),
        big("3", `Resample to ${f(p.sfreq, 0)} /s`, "the rate the CNN windows assume (4 s = 512 samples)"),
        h("p", { class: "side-note", html: `Result: <b>${p.shape[0]} electrodes × ${N(p.shape[1])} samples</b>, ${f(p.duration_s, 0)} s.` })));
    const v = new SignalView(wave, run, { view: "proc", timeline: false, initialSpan: 5 });
    await v.init();
    const set = async (m) => {
      raw.setAttribute("aria-pressed", m === "raw"); proc.setAttribute("aria-pressed", m === "proc");
      await v.setView(m);
      note.innerHTML = m === "raw" ? `<b>Before</b>: as recorded, ${run.sf0} samples per second · spacing ${v.spacing.raw} µV` : `<b>After</b>: average reference, 2–20 Hz, ${run.fs} samples per second · spacing ${v.spacing.proc} µV`;
      ns.viewMode = m;
    };
    raw.onclick = () => set("raw"); proc.onclick = () => set("proc");
    note.innerHTML = `<b>After</b>: average reference, 2–20 Hz, ${run.fs} samples per second · spacing ${v.spacing.proc} µV`;
  },

  async snapshots(canvas, run) {
    canvas.classList.add("solo");
    const wave = h("div", { id: "wave", style: { height: "100%" } });
    const img = h("img", { id: "snap-map", alt: "scalp map at the chosen instant" });
    const when = h("div", { class: "when num", id: "snap-time" });
    const film = h("div", { class: "film", id: "film" });
    const filmCap = h("p", { class: "cap", id: "film-cap", style: { margin: "6px 0 0" } });
    const top = h("div", { class: "snap-grid", style: { flex: 1, minHeight: 0 } },
      h("div", { style: { minHeight: 0 } }, wave),
      h("div", { class: "snap-arrow", "aria-hidden": "true" }, "→"),
      h("div", { class: "snap-map" }, when, img, h("div", { class: "cap", style: { margin: 0 } }, h("b", {}, "19 voltages → one map"), h("br"), "red = positive · blue = negative")));
    canvas.append(panel(cap(`<b>Processed EEG</b> (2–20 Hz, average reference). The gold line is one instant; each dot is one electrode’s voltage at that instant.`), top,
      h("div", { style: { flex: "none", marginTop: "8px" } }, film, filmCap)));
    const v = new SignalView(wave, run, { view: "proc", timeline: false, initialSpan: 1.2, range: [run.t0 + run.example_i / run.fs - 0.6, run.t0 + run.example_i / run.fs + 0.6], onPick: (i) => show(i) });
    await v.init();
    let seq = 0;
    async function show(i) {
      const my = ++seq;
      i = Math.max(3, Math.min(run.n - 5, i));
      const d = await api(`/api/runs/${run.run_id}/instant?i=${i}`);
      if (my !== seq) return;
      const vals = Object.fromEntries(d.channels.map((c, k) => [c, d.values_uv[k]]));
      v.cursorI = i;
      await v.setDots(i, vals);
      when.textContent = `${f(d.t, 3)} s`;
      const frames = Array.from({ length: 8 }, (_, k) => i - 3 + k);
      const all = await Promise.all(frames.map((j) => api(`/api/runs/${run.run_id}/instant?i=${j}`)));
      if (my !== seq) return;
      const vmax = niceMax(Math.max(...all.flatMap((x) => x.values_uv.map(Math.abs))));
      img.src = instantPng(run, i, vmax);
      // the run of snapshots around the instant that match the same map (the labels of step 7)
      let a = 3, b = 3;
      while (a > 0 && run.labels[frames[a - 1]] === run.labels[i]) a--;
      while (b < 7 && run.labels[frames[b + 1]] === run.labels[i]) b++;
      film.innerHTML = "";
      frames.forEach((j, k) => film.append(h("div", { class: `frame${k >= a && k <= b ? " same" : ""}${j === i ? " cur" : ""}` },
        h("img", { src: instantPng(run, j, vmax), alt: `snapshot ${k + 1}` }), `${k - 3 >= 0 ? "+" : "−"}${f(Math.abs(k - 3) * 1000 / run.fs, 1)} ms`)));
      const nSame = b - a + 1;
      filmCap.innerHTML = `<b>8 snapshots, ${f(1000 / run.fs, 1)} ms apart</b>, on one colour scale (±${vmax} µV). The ${nSame} under the gold line keep the same shape (about ${f(nSame * 1000 / run.fs, 0)} ms) while its strength rises and falls; then the shape changes.`;
      ns.snapshot = { i, frames, same: [a, b], vmax };
    }
    await show(run.example_i);
  },

  async peaks(canvas, run) {
    const fig = h("div", { class: "plot-fill", id: "gfp-plot" });
    const peakImg = h("img", { alt: "map at a GFP peak", id: "peak-map" }), lowImg = h("img", { alt: "map at a GFP low point", id: "low-map" });
    const peakV = h("div", { class: "v num" }), lowV = h("div", { class: "v num" });
    const peakT = h("div", { class: "cap" }), lowT = h("div", { class: "cap" });
    canvas.append(
      panel(cap(`<b>GFP</b>: how strong the scalp field is at each instant (the spread of the 19 voltages). <b style="color:${T.gold}">Gold dots</b> = peaks. Click a peak to compare.`), fig),
      h("aside", { class: "panel side" },
        h("div", { class: "pk-maps" },
          h("div", {}, h("div", { class: "h" }, "At a peak"), peakImg, peakV, peakT),
          h("div", { class: "low" }, h("div", { class: "h" }, "At a low point"), lowImg, lowV, lowT)),
        h("p", { class: "side-note" }, "The low point is the lowest GFP within 0.1 s of the peak. Same colour scale for both: at the peak the pattern is strong and clear; at the low point it is faint and less reliable."),
        big(N(run.steps.peaks.n_used), "GFP peaks used to find the patterns", run.steps.peaks.how)));
    const x = run.gfp.map((_, i) => run.t0 + i / run.fs);
    const t0 = run.t0 + run.example_i / run.fs - 1.5, t1 = t0 + 3;
    const inView = run.peak_idx.filter((i) => x[i] >= t0 && x[i] <= t1);
    let sel = inView.reduce((a, b) => (run.gfp[b] > run.gfp[a] ? b : a), inView[0]);
    await Plotly.newPlot(fig, [
      { type: "scattergl", mode: "lines", x, y: run.gfp, line: { color: T.text.primary, width: 1.6 }, hoverinfo: "skip", name: "GFP" },
      { type: "scattergl", mode: "markers", x: run.peak_idx.map((i) => x[i]), y: run.peak_idx.map((i) => run.gfp[i]), marker: { color: T.gold, size: 9 }, hoverinfo: "none", name: "peaks" },
      { type: "scatter", mode: "markers", x: [], y: [], marker: { color: T.gold, size: 20, line: { color: T.text.primary, width: 2 } }, hoverinfo: "skip", name: "sel" },
      { type: "scatter", mode: "markers", x: [], y: [], marker: { color: T.surface.inset, size: 16, line: { color: T.text.muted, width: 2 } }, hoverinfo: "skip", name: "low" }],
    font14({ margin: { l: 60, r: 14, t: 10, b: 48 }, dragmode: "zoom", hovermode: "x", hoverdistance: -1,
      xaxis: { range: [t0, t1], title: { text: "Time in the recording (s)", standoff: 8 }, gridcolor: T.surface.raised, zeroline: false },
      yaxis: { title: { text: "GFP (µV)", standoff: 8 }, fixedrange: true, gridcolor: T.surface.raised, zeroline: false, rangemode: "tozero" } }), plotConfig);
    fig.on("plotly_click", (ev) => {
      const t = Number(ev.points[0].x);
      const i = run.peak_idx.reduce((a, b) => (Math.abs(x[b] - t) < Math.abs(x[a] - t) ? b : a), run.peak_idx[0]);
      select(i);
    });
    async function select(i) {
      sel = i;
      // the lowest GFP within 0.1 s of the peak
      const w = Math.round(run.fs / 10);
      let low = i;
      for (let j = Math.max(0, i - w); j <= Math.min(run.n - 1, i + w); j++) if (run.gfp[j] < run.gfp[low]) low = j;
      const d = await api(`/api/runs/${run.run_id}/instant?i=${i}`);
      const vmax = niceMax(Math.max(...d.values_uv.map(Math.abs)));
      peakImg.src = instantPng(run, i, vmax);
      lowImg.src = instantPng(run, low, vmax);
      peakV.textContent = `${f(run.gfp[i], 1)} µV`;
      lowV.textContent = `${f(run.gfp[low], 1)} µV`;
      peakT.textContent = `GFP at ${f(x[i], 3)} s`;
      lowT.textContent = `GFP at ${f(x[low], 3)} s`;
      Plotly.restyle(fig, { x: [[x[i]], [x[low]]], y: [[run.gfp[i]], [run.gfp[low]]] }, [2, 3]);
      ns.peakPick = { peak: i, low, vmax };
    }
    await select(sel);
  },

  async fit(canvas, run) {
    const fr = run.steps.fit;
    const { maps } = await api(`/api/runs/${run.run_id}/peak_examples?n=4`);
    const byCluster = [...maps].sort((a, b) => a.cluster - b.cluster);
    const grid = h("div", { class: "clusters", id: "clusters" });
    byCluster.forEach((m, c) => grid.append(h("div", { class: "cluster", "data-cluster": c + 1 },
      h("div", { class: "nm" }, `Pattern ${c + 1}`),
      h("div", { class: "ex" }, ...m.examples.map((e) => h("img", { src: instantPng(run, e.i), alt: `peak at ${f(e.t, 2)} s`, title: `peak at ${f(e.t, 3)} s · |r| ${f(e.abs_r, 2)}` }))),
      h("div", { class: "down", "aria-hidden": "true" }, "↓"),
      h("img", { class: "final", src: `/api/runs/${run.run_id}/map/fitted/${m.k}.png`, alt: `fitted map ${c + 1}` }),
      h("div", { class: "cnt" }, h("b", {}, N(m.n_peaks)), " peaks look most like this"))));
    canvas.append(
      panel(cap(`<b>Top</b>: real peak snapshots from this recording, grouped with the pattern they match best. <b>Bottom</b>: the pattern found for each group.`), grid),
      h("aside", { class: "panel side" },
        big(f(fr.gev_peaks, 2), "GEV: share of the peaks’ signal the four maps explain", "a measure of map fit, not accuracy"),
        big("4", "maps: the classic number for comparison with published A–D maps"),
        big(`${fr.n_init}`, "restarts of the clustering; the best fit is kept", `seed ${fr.seed}, so the result is reproducible`),
        h("p", { class: "side-note" }, "Polarity is ignored: a map and its red↔blue mirror image count as the same pattern, because brain sources oscillate.")));
    ns.peakExamples = maps;
  },

  async name(canvas, run) {
    const nm = run.steps.name;
    const pairs = buildPairs(run);
    pairs.classList.add("demo-pairs");
    pairs.querySelectorAll(".card-sub, .dim").forEach((e) => e.remove());
    pairs.classList.remove("card");
    pairs.querySelector(".card-title").insertAdjacentElement("afterend", cap(`<b>Top</b>: the four maps fitted on this recording. <b>Bottom</b>: the published Koenig 2002 maps on the same 19 electrodes.`));
    canvas.append(panel(pairs),
      h("aside", { class: "panel side" },
        ...STATES.map((s, k) => big(f(nm.abs_r[s], 2), `fitted ${s} ↔ Koenig ${s}`)).map((e, k) => { e.querySelector(".n").style.color = stateColor(k); return e; }),
        h("p", { class: "side-note" }, `Pairs are chosen together, one-to-one, so no published map is used twice. ${nm.note}`)));
  },

  async timeline(canvas, run, opts = {}) {
    canvas.classList.add("solo");
    const host = h("div", { class: "demo-explorer", style: { height: "100%" } });
    canvas.append(host);
    await mountExplorer(host, run, { initialI: opts.exampleI ?? null });
    if (opts.exampleI !== undefined) await ns.setCursor(opts.exampleI, { span: 4 });
  },

  async measures(canvas, run) {
    canvas.classList.add("solo");
    const P = h("section", { class: "panel", style: { gap: "12px" } });
    canvas.append(P);
    const start = Math.max(0, run.example_i - 12), len = Math.round(run.fs / 4); // a quarter of a second
    const draw = () => {
      P.innerHTML = "";
      const k = pick, s = STATES[k], m = run.measures[k], col = stateColor(k);
      const seconds = run.n / run.fs, msPer = 1000 / run.fs;
      // excerpt: visits as blocks, each as wide as it lasts
      const seg = [];
      for (let i = start; i < start + len; i++) {
        const last = seg[seg.length - 1];
        if (last && last.k === run.labels[i]) last.n++; else seg.push({ k: run.labels[i], n: 1, first: i });
      }
      const strip = h("div", { class: "ex-strip", id: "excerpt" }), msRow = h("div", { class: "ex-ms" });
      seg.forEach((v, j) => {
        const clipped = (j === 0 && v.first === start && start > 0 && run.labels[start - 1] === v.k) || (j === seg.length - 1 && run.labels[start + len] === v.k);
        strip.append(h("div", { class: `v${v.k === k ? "" : " dim"}`, style: { flex: v.n, background: stateColor(v.k) }, title: `${STATES[v.k]}: ${v.n} samples` }, STATES[v.k]));
        msRow.append(h("span", { style: { flex: v.n, color: col } }, v.k === k && !clipped ? `${f(v.n * msPer, 0)} ms` : ""));
      });
      const picker = h("div", { class: "pick", id: "map-pick" }, h("span", { class: "cap", style: { margin: "0 6px 0 0" } }, h("b", {}, "Pick a map:")),
        ...STATES.map((x, j) => h("button", { type: "button", "aria-pressed": j === k, style: { background: stateColor(j) }, onclick: () => { pick = j; draw(); } }, x)));
      P.append(h("div", { class: "row", style: { justifyContent: "space-between" } }, picker,
        h("span", { class: "cap", style: { margin: 0 } }, `A quarter of a second of the timeline (${f(run.t0 + start / run.fs, 2)}–${f(run.t0 + (start + len) / run.fs, 2)} s). Each block is one visit; its width is how long it lasts.`)),
        h("div", { class: "excerpt" }, strip, msRow));
      // the three measures for the chosen map, each with its real arithmetic and the A-D comparison
      const bars = (vals, fmt, max) => h("div", { class: "mbars" }, ...vals.map((v, j) => h("div", { class: `mbar${j === k ? " sel" : ""}` },
        h("span", { style: { color: stateColor(j), fontWeight: 700 } }, STATES[j]), h("div", { class: "tr" }, h("div", { class: "fl", style: { width: `${(v / max) * 100}%`, background: stateColor(j) } })), h("span", { class: "val" }, fmt(v)))));
      const D = run.measures.map((x) => x.mean_duration_ms), O = run.measures.map((x) => x.occurrence_per_s), C = run.measures.map((x) => x.coverage_pct);
      // one second of the timeline with a tick at the start of every visit to the chosen map
      const s1 = Math.max(0, Math.min(run.n - run.fs, run.example_i - run.fs / 2)), ticks = h("div", { class: "tick-strip" });
      let count = 0;
      for (let i = s1; i < s1 + run.fs; i++) if (run.labels[i] === k && (i === 0 || run.labels[i - 1] !== k)) { count++; ticks.append(h("i", { style: { left: `${((i - s1) / run.fs) * 100}%`, background: col } })); }
      // how long the chosen map's visits last (whole recording): 1, 2, ... 8+ samples
      const lens = [];
      { let run0 = 0; for (let i = 0; i <= run.n; i++) { if (i < run.n && run.labels[i] === k) run0++; else if (run0) { lens.push(run0); run0 = 0; } } }
      const hist = Array.from({ length: 8 }, (_, j) => lens.filter((L) => (j === 7 ? L >= 8 : L === j + 1)).length), hmax = Math.max(...hist);
      const histEl = h("div", { class: "hist", id: "dur-hist" }, ...hist.map((c, j) => h("div", { class: "col" },
        h("span", { class: "c num" }, N(c)), h("div", { class: "b", style: { height: `${(c / hmax) * 100}%`, background: col } }),
        h("span", { class: "x num" }, `${f((j + 1) * msPer, 0)}${j === 7 ? "+" : ""}`))));
      // coverage as 100 squares (largest-remainder rounding of the four coverages)
      const raw = C.map((v) => v), fl = raw.map(Math.floor);
      let left = 100 - fl.reduce((a, b) => a + b, 0);
      raw.map((v, j) => [v - fl[j], j]).sort((a, b) => b[0] - a[0]).forEach(([, j]) => { if (left > 0) { fl[j]++; left--; } });
      const waffle = h("div", { class: "waffle", id: "cov-waffle" }, ...fl.flatMap((cnt, j) => Array.from({ length: cnt }, () => h("i", { class: j === k ? "" : "dim", style: { background: stateColor(j) } }))));
      P.append(h("div", { class: "mcards", id: "mcards" },
        h("div", { class: "mcard", "data-measure": "duration" }, h("div", { class: "q" }, "Duration · how long"), h("div", { class: "n num" }, `${f(m.mean_duration_ms, 1)} ms`),
          h("div", { class: "mean" }, `A visit to ${s} lasts ${f(m.mean_duration_ms, 1)} ms on average.`),
          h("div", { class: "calc", html: `<b>${N(m.n_samples)}</b> samples ÷ <b>${N(m.n_visits)}</b> visits = ${f(m.n_samples / m.n_visits, 2)} samples of ${f(msPer, 1)} ms` }),
          h("div", { class: "viz" }, h("div", { class: "viz-cap" }, `How long each of the ${N(m.n_visits)} visits to ${s} lasts (ms)`), histEl),
          bars(D, (v) => `${f(v, 1)} ms`, Math.max(...D))),
        h("div", { class: "mcard", "data-measure": "occurrence" }, h("div", { class: "q" }, "Occurrence · how often"), h("div", { class: "n num" }, `${f(m.occurrence_per_s, 1)} /s`),
          h("div", { class: "mean" }, `${s} starts a new visit ${f(m.occurrence_per_s, 1)} times per second.`),
          h("div", { class: "calc", html: `<b>${N(m.n_visits)}</b> visits ÷ <b>${f(seconds, 1)}</b> s` }),
          h("div", { class: "viz" }, h("div", { class: "viz-cap" }, `One second of the timeline: each tick is a new visit to ${s} (${count} here)`), ticks),
          bars(O, (v) => `${f(v, 1)} /s`, Math.max(...O))),
        h("div", { class: "mcard", "data-measure": "coverage" }, h("div", { class: "q" }, "Coverage · how much"), h("div", { class: "n num" }, PCT(m.coverage_pct)),
          h("div", { class: "mean" }, `${s} is the label ${PCT(m.coverage_pct)} of the time.`),
          h("div", { class: "calc", html: `<b>${N(m.n_samples)}</b> of <b>${N(run.n)}</b> samples` }),
          h("div", { class: "viz" }, h("div", { class: "viz-cap" }, "Each square = 1% of the recording"), waffle),
          h("div", { class: "cover-bar" }, ...C.map((v, j) => h("span", { class: j === k ? "" : "dim", style: { width: `${v}%`, background: stateColor(j) } }, j === k ? STATES[j] : ""))),
          bars(C, (v) => PCT(v), Math.max(...C)))),
        h("div", { class: "check", id: "measure-check", html: `The three fit together: <b>duration × occurrence = coverage</b> · ${f(m.mean_duration_ms, 1)} ms × ${f(m.occurrence_per_s, 1)} /s = ${PCT((m.mean_duration_ms / 1000) * m.occurrence_per_s * 100)}` }));
      ns.measurePick = { k, m, excerpt: { start, len, visits: seg.length }, ticks: count, hist, waffle: fl };
    };
    draw();
  },

  async transitions(canvas, run) {
    const diagram = h("div", { style: { flex: 1, minHeight: 0 } });
    const sentence = h("p", { class: "check", id: "trans-sentence", style: { margin: 0 } });
    const heat = h("div", { id: "trans", style: { height: "300px" } });
    const P = panel(h("div", { class: "row", style: { justifyContent: "space-between" } }, h("div", { class: "pick", id: "map-pick" }), cap("Arrow width = how often the timeline goes there next.")), diagram, sentence);
    canvas.append(P, h("aside", { class: "panel side" }, cap("<b>All maps at once</b>: row = from, column = to. Each row adds up to 1."), heat,
      h("p", { class: "side-note" }, `Only switches count: a map followed by itself is not a transition. ${N(run.steps.measures.n_transitions)} switches in this recording.`)));
    requestAnimationFrame(() => drawTransitions(heat, run));
    const C = run.transitions.conditional, Ncnt = run.transitions.counts;
    const draw = () => {
      const k = pick, NSv = "http://www.w3.org/2000/svg";
      const pk = P.querySelector("#map-pick");
      pk.innerHTML = "";
      pk.append(h("span", { class: "cap", style: { margin: "0 6px 0 0" } }, h("b", {}, "From map:")),
        ...STATES.map((x, j) => h("button", { type: "button", "aria-pressed": j === k, style: { background: stateColor(j) }, onclick: () => { pick = j; draw(); } }, x)));
      const W = 760, H = 420, pos = [[200, 90], [560, 90], [560, 330], [200, 330]], R = 50;
      const svg = document.createElementNS(NSv, "svg");
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("class", "trans-svg"); svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", `Where the timeline goes after map ${STATES[k]}`);
      const el = (tag, attrs, text) => { const e = document.createElementNS(NSv, tag); Object.entries(attrs).forEach(([a, v]) => e.setAttribute(a, v)); if (text !== undefined) e.textContent = text; svg.append(e); return e; };
      const defs = el("defs", {});
      STATES.forEach((_, j) => {
        const mk = document.createElementNS(NSv, "marker");
        Object.entries({ id: `tr-arrow-${j}`, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 4, markerHeight: 4, orient: "auto" }).forEach(([a, v]) => mk.setAttribute(a, v));
        const p = document.createElementNS(NSv, "path"); p.setAttribute("d", "M0 0L10 5L0 10z"); p.setAttribute("fill", stateColor(j)); mk.append(p); defs.append(mk);
      });
      const order = [0, 1, 2, 3].filter((j) => j !== k).sort((a, b) => C[k][b] - C[k][a]);
      for (const j of order) {
        const [x1, y1] = pos[k], [x2, y2] = pos[j], dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
        const w = 4 + 30 * C[k][j];
        el("line", { x1: x1 + ux * (R + 6), y1: y1 + uy * (R + 6), x2: x2 - ux * (R + 10 + w * 0.9), y2: y2 - uy * (R + 10 + w * 0.9), stroke: stateColor(j), "stroke-width": w, "stroke-linecap": "round", "marker-end": `url(#tr-arrow-${j})`, opacity: 0.9 });
        const mx = x1 + dx * 0.5 - uy * 26, my = y1 + dy * 0.5 + ux * 26;
        el("rect", { x: mx - 46, y: my - 22, width: 92, height: 36, rx: 8, fill: T.surface.inset, stroke: stateColor(j), "stroke-width": 1.5 });
        el("text", { x: mx, y: my + 3, "text-anchor": "middle", "font-size": 22, "font-weight": 700, fill: T.text.primary, "font-family": T.fonts.sans }, PCT(C[k][j] * 100, 0));
      }
      pos.forEach(([x, y], j) => {
        el("circle", { cx: x, cy: y, r: R, fill: stateColor(j), opacity: j === k ? 1 : 0.55, stroke: j === k ? T.text.primary : "none", "stroke-width": 3 });
        el("text", { x, y: y + 13, "text-anchor": "middle", "font-size": 38, "font-weight": 800, fill: T.text.onGold, "font-family": T.fonts.sans }, STATES[j]);
      });
      diagram.innerHTML = ""; diagram.append(svg);
      const tot = Ncnt[k].reduce((a, b, j) => a + (j === k ? 0 : b), 0);
      sentence.innerHTML = `After <b style="color:${stateColor(k)}">${STATES[k]}</b>, the next map is ${order.map((j) => `<b style="color:${stateColor(j)}">${STATES[j]}</b> ${PCT(C[k][j] * 100, 0)}`).join(", ")} of the time (${N(tot)} switches from ${STATES[k]}).`;
      ns.transPick = { k, probs: C[k], total: tot };
    };
    draw();
  },

  async cnn(canvas, run) {
    const c = run.cnn;
    const winFig = h("div", { id: "cnn-windows" }), raster = h("div", { id: "cnn-raster" });
    const label = h("span", { class: "cap", id: "win-label", style: { margin: 0 } });
    canvas.append(
      panel(h("div", { class: "row", style: { justifyContent: "space-between" } }, cap(`<b>The whole ${f(run.n / run.fs, 0)}-second timeline</b>, cut into ${c.n_windows} windows of 4 s. Click a window.`), label), winFig, raster),
      h("aside", { class: "panel side" }, flowSvg(),
        big(`${c.n_windows}`, "complete 4-s windows (512 samples each)", `${c.leftover_samples} samples (${f(c.leftover_s, 1)} s) left over at the end`),
        h("p", { class: "side-note" }, "This demo shows the input only. No model output is shown: the CNN for epilepsy has not been trained yet.")));
    const n = run.n, x = Array.from({ length: n }, (_, i) => run.t0 + i / run.fs), W = c.win / run.fs;
    const shapes = (sel) => [
      ...Array.from({ length: c.n_windows + 1 }, (_, j) => ({ type: "line", xref: "x", yref: "paper", x0: run.t0 + j * W, x1: run.t0 + j * W, y0: 0, y1: 1, line: { color: T.surface.inset, width: 3 } })),
      { type: "rect", xref: "x", yref: "paper", x0: run.t0 + c.n_windows * W, x1: run.t1, y0: 0, y1: 1, fillcolor: "rgba(14,21,27,0.75)", line: { width: 0 } },
      { type: "rect", xref: "x", yref: "paper", x0: run.t0 + sel * W, x1: run.t0 + (sel + 1) * W, y0: -0.04, y1: 1.04, line: { color: T.gold, width: 3 }, fillcolor: "rgba(0,0,0,0)", name: "selected" }];
    const ann = Array.from({ length: c.n_windows }, (_, j) => ({ x: run.t0 + (j + 0.5) * W, y: 1.02, xref: "x", yref: "paper", yanchor: "bottom", showarrow: false, text: `${j + 1}`, font: { size: 13, color: T.text.primary } }));
    let sel = 1;
    await Plotly.newPlot(winFig, [{ type: "heatmap", x, y: [0], z: [run.labels], zmin: -0.5, zmax: 3.5, colorscale: stateScale(), showscale: false, hoverinfo: "none" }],
      font14({ margin: { l: 44, r: 10, t: 26, b: 30 }, xaxis: { range: [run.t0, run.t1], fixedrange: true, tickfont: { size: 13 }, ticksuffix: " s" },
        yaxis: { fixedrange: true, showticklabels: false }, shapes: shapes(sel), annotations: ann }), { ...plotConfig, displayModeBar: false });
    winFig.on("plotly_click", (ev) => { const j = Math.floor((Number(ev.points[0].x) - run.t0) / W); if (j >= 0 && j < c.n_windows) showWin(j); });
    async function showWin(j) {
      sel = j;
      const w = await api(`/api/runs/${run.run_id}/cnn_window/${j}`);
      Plotly.relayout(winFig, { shapes: shapes(j) });
      label.innerHTML = `<b>Window ${j + 1} of ${w.n_windows}</b> · ${f(w.t_start, 1)}–${f(w.t_end, 1)} s · 4 rows × 512 samples`;
      drawWindow(raster, run, w, { big: true });
      ns.cnnWindow = w;
    }
    await showWin(sel);
  },
};

function flowSvg() {
  const NSv = "http://www.w3.org/2000/svg", svg = document.createElementNS(NSv, "svg");
  const steps = ["One window: 4 rows × 512", "Sequence CNN", "A score for each window", "Average over all windows", "One score per patient"];
  const H = 46, G = 22, Wd = 300;
  svg.setAttribute("viewBox", `0 0 ${Wd + 20} ${steps.length * H + (steps.length - 1) * G + 8}`);
  svg.setAttribute("class", "flow-svg"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", "How the CNN uses the windows");
  const el = (tag, attrs, text) => { const e = document.createElementNS(NSv, tag); Object.entries(attrs).forEach(([a, v]) => e.setAttribute(a, v)); if (text) e.textContent = text; svg.append(e); return e; };
  steps.forEach((s, j) => {
    const y = 4 + j * (H + G), first = j === 0;
    el("rect", { x: 10, y, width: Wd, height: H, rx: 9, fill: first ? "rgba(240,180,90,0.14)" : "none", stroke: first ? T.gold : T.border, "stroke-width": first ? 2 : 1.5 });
    el("text", { x: 10 + Wd / 2, y: y + H / 2 + 6, "text-anchor": "middle", "font-size": 17, "font-weight": first ? 700 : 500, fill: T.text.primary, "font-family": T.fonts.sans }, s);
    if (j < steps.length - 1) el("path", { d: `M${10 + Wd / 2} ${y + H + 3}V${y + H + G - 3}M${10 + Wd / 2 - 6} ${y + H + G - 9}L${10 + Wd / 2} ${y + H + G - 3}L${10 + Wd / 2 + 6} ${y + H + G - 9}`, fill: "none", stroke: T.gold, "stroke-width": 2 });
  });
  return svg;
}

// ---------------------------------------------------------------------------------------------- CNN window view (shared with the study page)
export function windowControls(run, overEl, winEl, { start = 1 } = {}) {
  let k = Math.min(start, run.cnn.n_windows - 1);
  const label = h("span", { class: "num", id: "win-label" });
  const prev = h("button", { class: "btn btn-ghost btn-small", type: "button", id: "win-prev" }, "◀");
  const next = h("button", { class: "btn btn-ghost btn-small", type: "button", id: "win-next" }, "▶");
  let sv = null;
  async function show() {
    const w = await api(`/api/runs/${run.run_id}/cnn_window/${k}`);
    label.textContent = `Window ${k + 1} of ${w.n_windows} · ${f(w.t_start, 3)}–${f(w.t_end, 3)} s · samples ${w.first_sample}–${w.first_sample + 511}`;
    sv.setHighlight(w.t_start, w.t_end, { zoom: true });
    drawWindow(winEl, run, w);
    prev.disabled = k === 0; next.disabled = k === w.n_windows - 1;
    ns.cnnWindow = w;
  }
  prev.onclick = () => { k = Math.max(0, k - 1); show(); };
  next.onclick = () => { k = Math.min(run.cnn.n_windows - 1, k + 1); show(); };
  return {
    el: h("div", { class: "toolbar" }, prev, label, next),
    async init() {
      sv = new SignalView(overEl, run, { timelineFrac: 0.2, initialSpan: 10 });
      await sv.init();
      await show();
    },
  };
}

export function drawWindow(el, run, w, { big = false } = {}) {
  const n = w.onehot[0].length;
  const x = Array.from({ length: n }, (_, i) => w.t_start + i / run.fs);
  const lab = run.labels.slice(w.first_sample, w.first_sample + n);
  // row 0: the timeline over this window; rows 1-4: one-hot rows A-D (cell = its state's colour where 1, empty where 0)
  const z = [lab, ...w.onehot.map((row, s) => row.map((v) => (v ? s : null)))];
  const y = ["timeline", ...STATES];
  const fs = big ? 16 : 12;
  Plotly.react(el, [{ type: "heatmap", x, y, z, zmin: -0.5, zmax: 3.5, colorscale: stateScale(), showscale: false, ygap: 3, hoverinfo: "none" }],
    plotBase({ margin: { l: big ? 96 : 44, r: 10, t: 6, b: 44 }, font: { family: `${T.fonts.sans}, sans-serif`, color: T.text.muted, size: big ? 14 : 12 },
      xaxis: { title: { text: big ? "Time in the recording (s) · 512 samples · a coloured cell = 1, empty = 0" : "Time in the recording (s) · 512 samples", standoff: 6 }, range: [w.t_start, w.t_end], fixedrange: true, gridcolor: T.surface.raised },
      yaxis: { autorange: "reversed", fixedrange: true, tickvals: y, ticktext: [big ? "timeline" : "A–D", ...STATES.map((s) => `<b><span style="color:${T.states[s]};font-size:${fs}px">${big ? `row ${s}` : s}</span></b>`)] },
      shapes: [{ type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 0.5, y1: 0.5, line: { color: T.border, width: 2 } }] }),
    { ...plotConfig, displayModeBar: false });
}
