// Building blocks shared by the demo walkthrough and the research outputs:
// the waveform+timeline explorer with the click inspector, fitted maps vs templates, measures.
import { SignalView } from "./signal.js";
import { api, f, h, pct, plotBase, plotConfig, stateColor, STATES, T } from "./util.js";

const ns = (window.__ns = window.__ns || {});

// ---------------------------------------------------------------------------------- explorer (plot + inspector)
export async function mountExplorer(host, run, { initialI = null, extraTools = [] } = {}) {
  const rawBtn = h("button", { type: "button", "aria-pressed": "false", id: "view-raw" }, "Raw");
  const procBtn = h("button", { type: "button", "aria-pressed": "true", id: "view-proc" }, "Processed");
  const chBtn = h("button", { class: "btn btn-ghost btn-small", type: "button", id: "ch-toggle" }, "Show all 19 channels");
  const viewNote = h("span", { class: "dim", style: { fontSize: "12.5px" }, id: "view-note" });
  const readout = h("span", { class: "readout num", id: "readout" });
  const wave = h("div", { id: "wave" });
  const plotCard = h("section", { class: "card plot-card" },
    h("div", { class: "toolbar" }, h("div", { class: "seg" }, rawBtn, procBtn), chBtn, ...extraTools, viewNote, readout),
    wave,
    h("div", { class: "dim hint", style: { fontSize: "12px" } }, "Click anywhere on the waveform or the A–D timeline to inspect that moment · ← → step one sample · drag to zoom in time"));
  const insp = buildInspector(run);
  host.append(h("div", { class: "top-row" }, plotCard, insp.el));

  const view = new SignalView(wave, run, { onPick: (i) => setCursor(i) });
  ns.view = view;
  await view.init();
  const noteFor = (v) => (v === "raw"
    ? `Raw: as recorded, original reference, ${run.sf0} Hz · trace spacing ${view.spacing.raw ?? "…"} µV`
    : `Processed: 2–20 Hz, average reference, ${run.fs} Hz · trace spacing ${view.spacing.proc ?? "…"} µV`);
  viewNote.textContent = noteFor("proc");
  ns.viewMode = "proc";

  async function setView(v) {
    rawBtn.setAttribute("aria-pressed", v === "raw"); procBtn.setAttribute("aria-pressed", v === "proc");
    await view.setView(v);
    if (ns.cursor) view.setCursor(ns.cursor.i, { follow: false });
    viewNote.textContent = noteFor(v);
    ns.viewMode = v;
  }
  rawBtn.onclick = () => setView("raw");
  procBtn.onclick = () => setView("proc");
  let all = false;
  chBtn.onclick = async () => {
    all = !all;
    chBtn.textContent = all ? `Show ${run.default_view.length} channels` : "Show all 19 channels";
    await view.setChannels(all ? run.channels : run.default_view);
    if (ns.cursor) view.setCursor(ns.cursor.i, { follow: false });
  };

  let pending = 0;
  async function setCursor(i, opts = {}) {
    i = Math.max(0, Math.min(run.n - 1, i));
    ns.cursor = { i, t: view.t(i) };
    view.setCursor(i, opts);
    readout.textContent = `cursor ${f(view.t(i), 3)} s · sample ${i}`;
    const my = ++pending;
    const d = await api(`/api/runs/${run.run_id}/instant?i=${i}`);
    if (my !== pending) return;
    insp.update(d);
    ns.inspector = d;
  }
  ns.setCursor = setCursor;
  ns.cursorShapes = () => view.cursorShapesX();
  const onKey = (e) => {
    if (!document.body.contains(wave)) { document.removeEventListener("keydown", onKey); return; }
    if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      e.stopImmediatePropagation();
      setCursor((ns.cursor ? ns.cursor.i : 0) + (e.key === "ArrowRight" ? 1 : -1) * (e.shiftKey ? 16 : 1));
    }
  };
  document.addEventListener("keydown", onKey, true);
  await setCursor(initialI ?? Math.min(run.n - 1, Math.round(5 * run.fs)));
  return { view, setCursor, inspector: insp };
}

export function buildInspector(run) {
  const time = h("div", { class: "insp-time num", id: "insp-time" });
  const img = h("img", { alt: "Scalp voltage map at the selected instant", id: "insp-map" });
  const scale = h("div", { class: "scale" });
  const bars = h("div", { class: "bars", id: "insp-bars" });
  const tag = h("span", { class: "state-tag", id: "insp-label" });
  const labelText = h("div", { id: "insp-label-text" });
  const sentence = h("p", { class: "sentence", id: "insp-sentence", style: { margin: 0 } });
  const smooth = h("p", { class: "smooth", id: "insp-smooth", style: { margin: 0 } });
  const rows = STATES.map((s, k) => {
    const fill = h("div", { class: "fill", style: { background: T.states[s], width: "0%" } });
    const val = h("span", { class: "val" }, "–");
    const row = h("div", { class: "bar", "data-state": s },
      h("img", { src: `/api/runs/${run.run_id}/map/fitted/${k}.png`, alt: `fitted map ${s}` }),
      h("span", { class: "state-tag", style: { background: T.states[s], width: "28px", height: "24px", fontSize: "13px" } }, s),
      h("div", { class: "track" }, fill), val);
    bars.append(row);
    return { row, fill, val };
  });
  const el = h("section", { class: "card inspector", id: "inspector" },
    h("div", { class: "insp-kicker" }, "This moment vs this recording’s fitted maps"),
    time,
    h("div", { class: "insp-map" }, img, h("div", {},
      h("div", { class: "card-sub", style: { margin: 0 } }, "Scalp voltage map: the 19 processed values at this instant (2–20 Hz, average reference)."),
      scale)),
    h("div", { class: "card-sub", style: { margin: "4px 0 0" } }, "Match |r| with each fitted map (sign ignored):"),
    bars,
    h("div", { class: "label-big" }, tag, labelText),
    sentence, smooth);

  function update(d) {
    time.textContent = `${f(d.t, 3)} s`;
    time.title = `sample ${d.i}`;
    img.src = `/api/runs/${run.run_id}/instant.png?i=${d.i}`;
    const mx = Math.max(...d.values_uv.map(Math.abs));
    scale.innerHTML = `Colour range ±${f(mx, 1)} µV<br>red = positive · blue = negative`;
    d.abs_r.forEach((r, k) => {
      rows[k].fill.style.width = `${Math.max(0, Math.min(1, r)) * 100}%`;
      rows[k].val.textContent = f(r, 2);
      rows[k].row.classList.toggle("win", k === d.winner);
    });
    tag.textContent = STATES[d.label];
    tag.style.background = stateColor(d.label);
    labelText.innerHTML = run.settings.min_segment && d.label !== d.label_argmax
      ? `Final label <b>${STATES[d.label]}</b> · best match alone: <b>${STATES[d.label_argmax]}</b>`
      : `Label <b>${STATES[d.label]}</b>${run.settings.min_segment ? " (best match and final label agree)" : ""}`;
    sentence.textContent = d.sentence;
    smooth.textContent = d.smoothing;
  }
  return { el, update };
}

// ---------------------------------------------------------------------------------- maps
export function buildPairs(run, { title = "Fitted maps vs published templates" } = {}) {
  const name = run.steps.name;
  const grid = h("div", { class: "pairs", id: "pairs" });
  STATES.forEach((s, k) => {
    grid.append(h("div", { class: "pair" },
      h("div", { class: "lab", style: { color: T.states[s] } }, `Fitted ${s}`),
      h("img", { src: `/api/runs/${run.run_id}/map/fitted/${k}.png`, alt: `fitted map ${s}` }),
      h("div", { class: "r num" }, `|r| = ${f(run.abs_r_template[k], 2)}`),
      h("img", { src: `/api/runs/${run.run_id}/map/template/${k}.png`, alt: `Koenig 2002 map ${s}` }),
      h("div", { class: "lab muted" }, `Koenig 2002 ${s}`)));
  });
  return h("section", { class: "card", id: "pairs-card" },
    h("h2", { class: "card-title" }, title),
    h("p", { class: "card-sub" }, "Top: the four maps fitted on this recording. Bottom: the published Koenig 2002 maps on the same 19 electrodes. Names come from one-to-one matching, polarity ignored; |r| is the match of each pair."),
    grid,
    h("p", { class: "dim", style: { fontSize: "12.5px", margin: "10px 0 0" } },
      `${name.note} Maps are fitted on this single recording; in a study they come from the training patients of each fold.`));
}

// ---------------------------------------------------------------------------------- measures
export function buildMeasures(run) {
  const tbl = h("table", { class: "t", id: "measures-table" },
    h("thead", {}, h("tr", {}, h("th", {}, "Map"), h("th", { class: "r" }, "Mean duration"), h("th", { class: "r" }, "Occurrence"), h("th", { class: "r" }, "Coverage"))),
    h("tbody", {}, ...run.measures.map((m, k) => h("tr", {},
      h("td", {}, h("span", { class: "dot", style: { background: stateColor(k) } }), m.state),
      h("td", { class: "r" }, `${f(m.mean_duration_ms, 1)} ms`),
      h("td", { class: "r" }, `${f(m.occurrence_per_s, 1)} /s`),
      h("td", { class: "r" }, pct(m.coverage_pct))))));
  const trans = h("div", { id: "trans" });
  const card = h("section", { class: "card", id: "measures-card" },
    h("h2", { class: "card-title" }, "Measures"),
    h("p", { class: "card-sub" }, "Per map, from the label of every sample. Transitions: P(k → j) over switches only; repeats of the same label are not counted."),
    h("div", { class: "measures-grid" }, tbl, trans),
    h("div", { class: "gev" }, h("b", {}, `GEV ${f(run.gev_all, 3)}`), h("span", { class: "muted" }, ` over all samples (${f(run.gev_peaks, 3)} at the GFP peaks): a measure of map fit, not accuracy.`)));
  requestAnimationFrame(() => drawTransitions(trans, run));
  return card;
}

export function drawTransitions(el, run) {
  const C = run.transitions.conditional, N = run.transitions.counts;
  const z = C.map((row, i) => row.map((v, j) => (i === j ? null : v)));
  const text = C.map((row, i) => row.map((v, j) => (i === j ? "–" : `${f(v, 2)}`)));
  const hover = C.map((row, i) => row.map((v, j) => (i === j ? "" : `${STATES[i]} → ${STATES[j]}: ${f(v, 3)} (${N[i][j]} switches)`)));
  const lab = STATES.map((s) => `<b><span style="color:${T.states[s]}">${s}</span></b>`);
  Plotly.newPlot(el, [{ type: "heatmap", z, x: lab, y: lab, text, texttemplate: "%{text}", hovertext: hover, hoverinfo: "text",
    colorscale: [[0, T.surface.raised], [1, T.gold]], zmin: 0, zmax: 1, showscale: false, xgap: 2, ygap: 2,
    textfont: { color: T.text.primary, size: 13 } }],
  plotBase({ margin: { l: 44, r: 6, t: 6, b: 40 }, xaxis: { title: { text: "to", standoff: 4 }, side: "bottom", fixedrange: true, showgrid: false, zeroline: false },
    yaxis: { title: { text: "from", standoff: 4 }, autorange: "reversed", fixedrange: true, showgrid: false, zeroline: false } }), { ...plotConfig, displayModeBar: false });
}

// ---------------------------------------------------------------------------------- research outputs (plain)
export async function renderOutputs(host, run) {
  host.innerHTML = "";
  const sp = run.steps.segment;
  host.append(h("div", { class: "res-head" },
    h("h2", { class: "card-title", style: { marginRight: "auto", fontSize: "17px" } }, `Outputs · ${run.file}`),
    h("a", { class: "btn btn-primary btn-small", href: `/api/runs/${run.run_id}/export.zip`, download: "", id: "export-btn" }, "Export ZIP")));
  host.append(h("div", { class: "facts" },
    fact("Segment", `${f(sp.tmin, 2)}–${f(sp.tmax, 2)} s`), fact("How chosen", { marker: "marker", full: "full recording", manual: "manual" }[sp.method]),
    fact("Samples (128 Hz)", run.n.toLocaleString()), fact("GFP peaks", run.steps.peaks.n_used),
    fact("GEV (map fit)", f(run.gev_all, 3)), fact("CNN windows", `${run.cnn.n_windows} × 4×512`)));
  if (sp.method === "full") host.append(h("div", { class: "notice" }, "No “eyes closed” marker matched, so the full recording was analysed."));
  if (sp.note) host.append(h("div", { class: "notice" }, sp.note));
  const seq = h("div", { id: "out-seq", style: { height: "320px" } });
  host.append(h("section", { class: "card section-gap" }, h("h3", { class: "card-title" }, "A–D sequence"),
    h("p", { class: "card-sub" }, "Processed EEG (2–20 Hz, average reference, 128 Hz) with the label of every sample underneath."), seq));
  host.append(h("div", { class: "maps-row section-gap" }, buildPairs(run, { title: "Microstate maps: fitted vs published templates" }), buildMeasures(run)));
  const v = new SignalView(seq, run, { timelineFrac: 0.16 });
  await v.init();
}

function fact(k, v) { return h("div", { class: "fact" }, h("div", { class: "k" }, k), h("div", { class: "v num" }, v)); }
