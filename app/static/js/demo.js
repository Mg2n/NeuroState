// The interactive demo: one fixed public recording, every view from the same precomputed run (app/cache/demo).
import { howTo } from "./howto.js";
import { buildMeasures, buildPairs, mountExplorer } from "./results.js";
import { SignalView } from "./signal.js";
import { api, f, h, plotBase, plotConfig, stateScale, STATES, T } from "./util.js";

const ns = (window.__ns = window.__ns || {});

const STAGES = [
  { id: "recording", title: "The recording", step: "read" },
  { id: "prepare", title: "Preprocessing", step: "prepare" },
  { id: "peaks", title: "GFP peaks", step: "peaks" },
  { id: "fit", title: "Four maps", step: "fit" },
  { id: "name", title: "Names A–D", step: "name" },
  { id: "timeline", title: "Every moment labelled", step: "label" },
  { id: "measures", title: "Measures", step: "measures" },
  { id: "cnn", title: "CNN input", step: "cnn" },
];

let RUN = null;
let current = 0;

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
  const exampleBtn = h("button", { class: "btn btn-primary", type: "button", id: "show-example" }, "Show an example");
  const nav = h("nav", { class: "stages", id: "stages" });
  const body = h("div", { class: "stage-body", id: "stage-body" });
  const prev = h("button", { class: "btn btn-ghost", type: "button", id: "stage-prev" }, "← Back");
  const next = h("button", { class: "btn", type: "button", id: "stage-next" }, "Next →");
  const s = RUN.steps;
  view.append(
    h("section", { class: "demo-head" },
      h("div", {},
        h("div", { class: "kicker" }, "Interactive demo · one public EEG recording"),
        h("h1", {}, "From voltages to maps to a timeline."),
        h("p", { class: "muted demo-sub" }, `PhysioNet EEG Motor Movement/Imagery, participant S001, eyes-closed baseline (${f(s.read.duration_s, 0)} s, ${s.read.n_channels} channels, ${f(s.read.sfreq, 0)} Hz). Every panel shows the same run of the NeuroState pipeline, computed once and bundled with the demo.`)),
      h("div", { class: "demo-actions" }, exampleBtn)),
    nav, body,
    h("div", { class: "stage-foot" }, prev, h("span", { class: "dim", style: { fontSize: "12.5px" } }, "Keys: 1–8 jump to a step · ← → move between steps (on step 6 they step one sample)"), next));

  STAGES.forEach((st, k) => nav.append(h("button", { type: "button", class: "stage-pill", "data-stage": st.id, onclick: () => go(k) },
    h("span", { class: "n" }, k + 1), st.title)));
  prev.onclick = () => go(current - 1);
  next.onclick = () => go(current + 1);
  exampleBtn.onclick = () => showExample();

  async function go(k, opts = {}) {
    current = Math.max(0, Math.min(STAGES.length - 1, k));
    nav.querySelectorAll(".stage-pill").forEach((b, i) => { b.classList.toggle("active", i === current); b.classList.toggle("seen", i < current); });
    prev.disabled = current === 0;
    next.disabled = current === STAGES.length - 1;
    next.textContent = current === STAGES.length - 1 ? "End of walkthrough" : `Next: ${STAGES[current + 1].title} →`;
    ns.stage = STAGES[current].id;
    body.innerHTML = "";
    body.classList.remove("enter"); void body.offsetWidth; body.classList.add("enter");
    await STAGE_RENDER[STAGES[current].id](body, RUN, opts);
    ns.stageReady = STAGES[current].id;
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
    if (/^[1-8]$/.test(e.key)) go(Number(e.key) - 1);
    else if (e.key === "ArrowRight") go(current + 1);
    else if (e.key === "ArrowLeft") go(current - 1);
  };
  document.addEventListener("keydown", onKey);
  await go(stage !== null ? stage : 0);
}

// ---------------------------------------------------------------------------------------------- stage helpers
function stageFrame(k, lede, main, side) {
  const st = STAGES[k];
  const how = h("div", { class: "howto-wrap" }, howTo(st.step, RUN.steps[st.step]));
  const howBtn = h("button", { class: "btn btn-ghost btn-small how-btn", type: "button", "aria-expanded": "false" }, "How it works");
  howBtn.onclick = () => { const o = how.classList.toggle("open"); howBtn.setAttribute("aria-expanded", o); };
  return h("div", { class: "stage" },
    h("div", { class: "stage-title" }, h("div", { class: "kicker" }, `Step ${k + 1} of ${STAGES.length}`), h("h2", {}, st.title), h("p", { class: "stage-lede" }, lede)),
    h("div", { class: side ? "stage-grid" : "" }, main, side ? h("aside", { class: "card stage-side" }, side, howBtn, how) : null),
    side ? null : h("div", {}, howBtn, how));
}

const kv = (k, v) => h("div", { class: "kv" }, h("span", { class: "k" }, k), h("span", { class: "v num" }, v));

// ---------------------------------------------------------------------------------------------- stages
const STAGE_RENDER = {
  async recording(body, run) {
    const r = run.steps.read, sg = run.steps.segment;
    const wave = h("div", { class: "stage-plot", id: "wave" });
    body.append(stageFrame(0, "The EDF file holds sampled voltages from every electrode. NeuroState keeps the 19 standard 10–20 electrodes, matched by name.",
      h("section", { class: "card plot-card" }, h("div", { class: "toolbar" }, h("span", { class: "dim", style: { fontSize: "12.5px" } }, `As recorded: original reference, ${f(r.sfreq, 0)} Hz, µV · ${run.default_view.length} of the 19 electrodes shown`)), wave),
      h("div", {},
        kv("Channels in the file", r.n_channels), kv("Standard channels found", `${r.recognised} / 19`),
        kv("Renamed (new → old names)", Object.entries(r.aliases_applied).map(([a, b]) => `${b}→${a}`).join(", ") || "none"),
        kv("Sampling rate", `${f(r.sfreq, 0)} Hz`), kv("Duration", `${f(r.duration_s, 1)} s`),
        kv("Segment analysed", `${f(sg.tmin, 1)}–${f(sg.tmax, 1)} s`),
        h("p", { class: "muted side-note" }, sg.method === "full" ? "This recording is one eyes-closed baseline with no “eyes closed” marker, so the full recording is analysed." : sg.how),
        h("p", { class: "dim side-note" }, `File SHA-256 ${run.file_sha256.slice(0, 16)}… matches PhysioNet’s published checksum.`))));
    const v = new SignalView(wave, run, { view: "raw", timeline: false, initialSpan: 6 });
    await v.init();
  },

  async prepare(body, run) {
    const p = run.steps.prepare;
    const wave = h("div", { class: "stage-plot", id: "wave" });
    const raw = h("button", { type: "button", "aria-pressed": "false", id: "view-raw" }, "Raw");
    const proc = h("button", { type: "button", "aria-pressed": "true", id: "view-proc" }, "Processed");
    const note = h("span", { class: "dim", style: { fontSize: "12.5px" } });
    body.append(stageFrame(1, "Each electrode is re-expressed relative to the average of all 19, then band-pass filtered to 2–20 Hz and resampled to 128 Hz. Toggle to compare.",
      h("section", { class: "card plot-card" }, h("div", { class: "toolbar" }, h("div", { class: "seg" }, raw, proc), note), wave),
      h("div", {},
        h("ol", { class: "mini-steps" },
          h("li", {}, h("b", {}, "Average reference: "), "subtract the mean of the 19 electrodes at each instant"),
          h("li", {}, h("b", {}, "Band-pass 2–20 Hz: "), "zero-phase FIR filter (the band of the Koenig 2002 maps)"),
          h("li", {}, h("b", {}, `Resample to ${f(p.sfreq, 0)} Hz: `), "the rate the CNN windows assume")),
        kv("Result", `${p.shape[0]} channels × ${p.shape[1].toLocaleString()} samples`), kv("Length", `${f(p.duration_s, 1)} s`),
        h("p", { class: "dim side-note" }, "A 1–40 Hz copy is made the same way for the waveform model; microstates use the 2–20 Hz copy."))));
    const v = new SignalView(wave, run, { view: "proc", timeline: false, initialSpan: 6 });
    await v.init();
    const set = async (m) => { raw.setAttribute("aria-pressed", m === "raw"); proc.setAttribute("aria-pressed", m === "proc"); await v.setView(m);
      note.textContent = m === "raw" ? `Raw: original reference, ${run.sf0} Hz · spacing ${v.spacing.raw} µV` : `Processed: 2–20 Hz, average reference, ${run.fs} Hz · spacing ${v.spacing.proc} µV`; };
    raw.onclick = () => set("raw"); proc.onclick = () => set("proc");
    note.textContent = `Processed: 2–20 Hz, average reference, ${run.fs} Hz · spacing ${v.spacing.proc} µV`;
  },

  async peaks(body, run) {
    const p = run.steps.peaks;
    const fig = h("div", { class: "stage-plot", id: "gfp-plot" });
    body.append(stageFrame(2, "Global field power (GFP) measures how strong the scalp field is at each instant. Its peaks are the moments with the clearest maps; only these go into the clustering.",
      h("section", { class: "card plot-card" }, h("div", { class: "toolbar" }, h("span", { class: "dim", style: { fontSize: "12.5px" } }, "GFP of the processed EEG · gold dots = the GFP peaks used for clustering · drag to zoom")), fig),
      h("div", {}, kv("GFP peaks found", p.n_local_maxima.toLocaleString()), kv("Used for clustering", p.n_used.toLocaleString()), kv("Cap", p.cap.toLocaleString()),
        h("p", { class: "muted side-note" }, p.how[0].toUpperCase() + p.how.slice(1) + "."))));
    const x = run.gfp.map((_, i) => run.t0 + i / run.fs);
    const px = run.peak_idx.map((i) => x[i]), py = run.peak_idx.map((i) => run.gfp[i]);
    await Plotly.newPlot(fig, [
      { type: "scattergl", mode: "lines", x, y: run.gfp, line: { color: T.text.primary, width: 1.2 }, hoverinfo: "skip", name: "GFP" },
      { type: "scattergl", mode: "markers", x: px, y: py, marker: { color: T.gold, size: 7 }, hoverinfo: "skip", name: "peaks" }],
    plotBase({ margin: { l: 56, r: 10, t: 8, b: 42 }, dragmode: "zoom",
      xaxis: { range: [run.t0, run.t0 + 4], title: { text: "Time in the recording (s)", standoff: 6 }, gridcolor: T.surface.raised, zeroline: false },
      yaxis: { title: { text: "GFP (µV)", standoff: 6 }, fixedrange: true, gridcolor: T.surface.raised, zeroline: false, rangemode: "tozero" } }), plotConfig);
  },

  async fit(body, run) {
    const fr = run.steps.fit, order = run.steps.name.cluster_for_ABCD;
    const grid = h("div", { class: "pairs" });
    for (let c = 0; c < 4; c++) {
      const j = order.indexOf(c);
      grid.append(h("div", { class: "pair" }, h("div", { class: "lab muted" }, `Cluster ${c + 1}`),
        h("img", { src: `/api/runs/${run.run_id}/map/fitted/${j}.png`, alt: `fitted cluster ${c + 1}` })));
    }
    body.append(stageFrame(3, "Modified k-means groups the peak maps into four recurring scalp maps. It ignores polarity, so a map and its red↔blue mirror count as the same map.",
      h("section", { class: "card" }, h("div", { class: "card-sub" }, "The four maps fitted on this recording (not yet named; polarity drawn to match the reference maps for readability)."), grid),
      h("div", {}, kv("Method", "modified k-means (Pycrostates)"), kv("Restarts (n_init)", fr.n_init), kv("Seed", fr.seed), kv("Peaks clustered", fr.n_peaks.toLocaleString()),
        kv("GEV at the peaks", f(fr.gev_peaks, 3)), h("p", { class: "muted side-note" }, "GEV is the share of the signal’s variance the four maps explain: a measure of map fit, not accuracy."))));
  },

  async name(body, run) {
    const nm = run.steps.name;
    body.append(stageFrame(4, "Each fitted map is paired one-to-one with a published reference map (Koenig et al. 2002) by spatial correlation, sign ignored, and takes its name.",
      buildPairs(run),
      h("div", {}, ...STATES.map((s) => kv(`Fitted ${s} ↔ Koenig ${s}`, `|r| = ${f(nm.abs_r[s], 3)}`)), h("p", { class: "muted side-note" }, nm.note),
        h("p", { class: "dim side-note" }, "|r| = 1 means an identical shape. The names are provisional labels for comparison with other studies."))));
  },

  async timeline(body, run, opts = {}) {
    const lab = run.steps.label;
    const host = h("div", {});
    body.append(stageFrame(5, `Every one of the ${lab.n_samples.toLocaleString()} samples takes the label of the fitted map it matches best. Click any moment to see why it got its label, or press “Show an example”.`, host, null));
    await mountExplorer(host, run, { initialI: opts.exampleI ?? null });
    if (opts.exampleI !== undefined) await ns.setCursor(opts.exampleI, { span: 4 });
  },

  async measures(body, run) {
    body.append(stageFrame(6, "The timeline is summarised per map: how long each visit lasts, how often the map appears, how much of the time it covers, and which map follows which.",
      buildMeasures(run), null));
  },

  async cnn(body, run) {
    const c = run.cnn;
    const over = h("div", { id: "ex-overview" }), win = h("div", { id: "ex-window" });
    const ctl = windowControls(run, over, win);
    body.append(stageFrame(7, "The A–D timeline is cut into 4-second windows of 512 samples. Each window becomes four rows, one per map, with a 1 wherever that map is present: the input of the sequence CNN.",
      h("section", { class: "card" }, ctl.el, over, win),
      h("div", {}, kv("Complete windows", c.n_windows), kv("Window shape", c.window_shape.join(" × ")), kv("Left over", `${c.leftover_samples} samples (${f(c.leftover_s, 2)} s)`),
        h("p", { class: "muted side-note" }, "The CNN scores each window; the window scores are averaged into one score per patient. This demo shows the input only: no model output is shown."),
        h("a", { href: "#/research", class: "btn btn-small" }, "Epilepsy research →"))));
    await ctl.init();
  },
};

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

export function drawWindow(el, run, w) {
  const n = w.onehot[0].length;
  const x = Array.from({ length: n }, (_, i) => w.t_start + i / run.fs);
  const lab = run.labels.slice(w.first_sample, w.first_sample + n);
  // row 0: the timeline over this window; rows 1-4: one-hot rows A-D (cell = its state's colour where 1, empty where 0)
  const z = [lab, ...w.onehot.map((row, s) => row.map((v) => (v ? s : null)))];
  const y = ["timeline", ...STATES];
  Plotly.react(el, [{ type: "heatmap", x, y, z, zmin: -0.5, zmax: 3.5, colorscale: stateScale(), showscale: false, ygap: 3, hoverinfo: "none" }],
    plotBase({ margin: { l: 44, r: 10, t: 6, b: 40 },
      xaxis: { title: { text: "Time in the recording (s) · 512 samples", standoff: 6 }, range: [w.t_start, w.t_end], fixedrange: true, gridcolor: T.surface.raised },
      yaxis: { autorange: "reversed", fixedrange: true, tickvals: y, ticktext: ["A–D", ...STATES.map((s) => `<b><span style="color:${T.states[s]}">${s}</span></b>`)] },
      shapes: [{ type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 0.5, y1: 0.5, line: { color: T.border, width: 1 } }] }),
    { ...plotConfig, displayModeBar: false });
}
