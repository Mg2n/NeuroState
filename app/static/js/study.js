// Epilepsy research: real processing of compatible recordings (background jobs), how sequences become CNN input,
// and the CNN results section, which stays in the pending state until a real results file exists.
// The Alzheimer's pilot is a separate panel below, outside the epilepsy section.
import { windowControls } from "./demo.js";
import { renderOutputs } from "./results.js";
import { api, f, h, plotBase, plotConfig, T } from "./util.js";

const ns = (window.__ns = window.__ns || {});
const STATUS_TEXT = { pending: "Epilepsy training pending", training: "Epilepsy training in progress",
  trained: "Epilepsy model trained · held-out evaluation pending", evaluated: "Epilepsy model evaluated on held-out patients" };

export function statusBadge(st) {
  const res = st && st.state === "results" ? st.results : null;
  const s = res ? res.status : "pending";
  return h("span", { class: `chip ${s === "evaluated" ? "chip-green" : "chip-pending"}`, id: "epi-status" }, STATUS_TEXT[s]);
}

export async function studyStatus() {
  try { return await api("/api/study/epilepsy"); } catch (_) { return { state: "pending" }; }
}

let pollTimer = null;

export async function renderStudy(view) {
  view.innerHTML = "";
  clearTimeout(pollTimer);
  const st = await studyStatus();
  ns.study = st;
  const epi = h("div", { id: "epilepsy-study" });
  view.append(epi);
  epi.append(h("section", { class: "study-head" },
    h("div", { class: "kicker" }, "Lead application · epilepsy research"),
    h("h1", {}, "Epilepsy research"),
    h("p", { class: "study-q", id: "study-question" }, "Can a CNN learn microstate sequence patterns that distinguish patients with epilepsy from patients without epilepsy?"),
    statusBadge(st)));

  // 1. processing ---------------------------------------------------------------------------------------
  const jobsBox = h("div", { id: "jobs" });
  const outBox = h("div", { id: "job-output" });
  const input = h("input", { type: "file", accept: ".edf,.EDF", multiple: true, class: "hidden", id: "edf-input" });
  const zone = h("label", { class: "drop", for: "edf-input" }, h("b", {}, "Add compatible EDF recordings"), h("br"),
    h("span", { class: "dim" }, "drop files here or click to choose · processed on this computer · 19 standard 10–20 electrodes needed"), input);
  const tmin = h("input", { type: "number", step: "0.1", min: "0", placeholder: "auto", id: "tmin" });
  const tmax = h("input", { type: "number", step: "0.1", min: "0", placeholder: "auto", id: "tmax" });
  const minSeg = h("select", { id: "min-seg" }, h("option", { value: "0" }, "None (default)"), ...[2, 3, 4, 5, 6, 8].map((n) => h("option", { value: n }, `${n} samples`)));
  const send = async (files) => {
    for (const file of files) {
      const fd = new FormData();
      fd.append("file", file); fd.append("tmin", tmin.value); fd.append("tmax", tmax.value); fd.append("min_segment", minSeg.value);
      await api("/api/research/upload", { method: "POST", body: fd });
    }
    poll();
  };
  input.onchange = () => input.files.length && send([...input.files]);
  zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("over"); };
  zone.ondragleave = () => zone.classList.remove("over");
  zone.ondrop = (e) => { e.preventDefault(); zone.classList.remove("over"); send([...e.dataTransfer.files]); };
  const sampleBtn = h("button", { class: "btn btn-small", type: "button", id: "process-sample" }, "Process the public test file (S001R02)");
  sampleBtn.onclick = async () => { await api("/api/research/sample", { method: "POST" }); poll(); };
  epi.append(h("section", { class: "card section-gap", id: "processing" },
    h("h2", { class: "card-title" }, "Process recordings"),
    h("p", { class: "card-sub" }, "Each file is checked from its header, then run through the NeuroState pipeline in the background: maps, the A–D sequence, and duration, occurrence, coverage and transitions."),
    zone,
    h("div", { class: "row", style: { marginTop: "10px" } }, sampleBtn,
      h("details", { class: "advanced" }, h("summary", {}, "Segment and smoothing options"),
        h("div", { class: "manual", style: { marginTop: "8px" } }, h("label", {}, "Manual start (s)", tmin), h("label", {}, "Manual end (s)", tmax),
          h("label", {}, "Smoothing (minimum segment)", minSeg),
          h("span", { class: "dim", style: { fontSize: "12.5px", maxWidth: "360px" } }, "Default: first “eyes closed” marker to the next marker, else the full recording; no smoothing (as the pipeline).")))),
    jobsBox, outBox));

  // 2. CNN input --------------------------------------------------------------------------------------------
  const exBtn = h("button", { class: "btn btn-small", type: "button", id: "example-cnn-btn" }, "Show the example CNN input");
  const exBox = h("div", { id: "example-cnn" });
  exBtn.onclick = async () => {
    exBtn.disabled = true;
    try {
      const run = await api("/api/demo");
      const over = h("div", { id: "ex-overview" }), win = h("div", { id: "ex-window" });
      const ctl = windowControls(run, over, win);
      exBox.append(h("h3", { class: "card-title", style: { marginTop: "14px" } }, "Example CNN input"),
        h("p", { class: "card-sub", id: "example-caption" }, "Public recording from a dataset that is not about epilepsy (PhysioNet EEGMMIDB S001R02, the demo recording). It shows the input format only."),
        ctl.el, over, win);
      await ctl.init();
    } catch (e) {
      exBox.append(h("div", { class: "notice error" }, "The demo bundle is not built yet (app/tools/fetch_public_inputs.py)."));
    }
  };
  epi.append(h("section", { class: "card section-gap", id: "cnn-input" },
    h("h2", { class: "card-title" }, "How microstate sequences become CNN input"),
    h("ol", { class: "flow" },
      h("li", {}, "The A–D timeline is cut into 4-s windows (512 samples at 128 Hz)."),
      h("li", {}, "Each window becomes 4 rows, one per map: one-hot."),
      h("li", {}, "The CNN scores each window."),
      h("li", {}, "The window scores are averaged into one score per patient."),
      h("li", {}, "Evaluation is at patient level: each patient is entirely in training or entirely in testing.")),
    h("div", { class: "row", style: { marginTop: "12px" } }, exBtn), exBox));

  // 3. CNN results -------------------------------------------------------------------------------------------
  epi.append(cnnResults(st));

  // 4. Alzheimer's pilot (separate) ---------------------------------------------------------------------------
  const alz = await api("/api/study/alzheimers-pilot");
  if (alz.panel) view.append(alzPanel(alz.panel));

  poll();

  async function poll() {
    clearTimeout(pollTimer);
    if (!document.body.contains(jobsBox)) return;
    const { jobs } = await api("/api/research/jobs");
    renderJobs(jobsBox, outBox, jobs);
    if (jobs.some((j) => j.status === "queued" || j.status === "running")) pollTimer = setTimeout(poll, 600);
  }
}

const STATUS_LABEL = { queued: "Queued", running: "Processing", done: "Done", incompatible: "Not compatible", failed: "Failed" };

function renderJobs(box, outBox, jobs) {
  ns.jobs = jobs;
  box.innerHTML = "";
  if (!jobs.length) return;
  const tb = h("tbody", {});
  jobs.forEach((j) => {
    const detail = j.status === "running" ? `step ${j.steps_done + 1} of ${j.n_steps}${j.step_title ? ` · last finished: ${j.step_title}` : ""}`
      : j.status === "done" ? `${j.n_steps} steps in ${f(j.seconds, 1)} s`
      : j.status === "incompatible" ? (j.problems || []).map((p) => p.message).join(" ")
      : j.status === "failed" ? j.message : "waiting for the worker";
    const view = j.status === "done" ? h("button", { class: "btn btn-small", type: "button", "data-job": j.job_id, onclick: () => openJob(outBox, j) }, "View outputs") : null;
    tb.append(h("tr", { "data-status": j.status, "data-job": j.job_id },
      h("td", {}, j.name),
      h("td", {}, h("span", { class: `status status-${j.status}` }, STATUS_LABEL[j.status])),
      h("td", { class: "muted", style: { fontSize: "13px" } }, detail,
        j.status === "incompatible" ? h("div", { class: "dim" }, (j.problems || []).map((p) => `Found: ${p.found} · needs: ${p.needed}`).join(" | ")) : null),
      h("td", { class: "r" }, view)));
  });
  box.append(h("table", { class: "t jobs", style: { marginTop: "14px" } },
    h("thead", {}, h("tr", {}, h("th", {}, "Recording"), h("th", {}, "Status"), h("th", {}, "Details"), h("th", {}))), tb));
}

async function openJob(outBox, j) {
  const run = await api(`/api/runs/${j.run_id}`);
  ns.researchRun = run;
  await renderOutputs(outBox, run);
  outBox.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ------------------------------------------------------------------------------------------------ CNN results
function cnnResults(st) {
  const box = h("section", { class: "card section-gap", id: "cnn-results" },
    h("h2", { class: "card-title" }, "CNN results: epilepsy vs no epilepsy"));
  if (st.state !== "results") {
    box.append(h("div", { class: "row" }, statusBadge(st)),
      h("p", { class: "muted", id: "pending-text", style: { maxWidth: "820px" } },
        "No epilepsy model has been trained yet; the epilepsy recordings are still to arrive. When training and evaluation have run, this section shows the training cohort, the logged training values, the held-out performance and, if there are comparable runs at several training sizes, a learning curve, all read from the results file."));
    return box;
  }
  const r = st.results;
  box.append(h("div", { class: "row" }, statusBadge(st), h("span", { class: "dim" }, `classes: ${r.labels.join(" vs ")} · results file generated ${r.generated_at}`)));
  if (r.cohort) {
    const c = r.cohort;
    const tiles = [["Recordings ingested", c.recordings_ingested], ["Recordings processed", c.recordings_processed],
      ["Patients in training", c.unique_patients_training], ["Patients held out for testing", c.unique_patients_test],
      ["Eligible patients available", c.eligible_patients_available]].filter(([, v]) => v !== null && v !== undefined);
    box.append(h("h3", { class: "card-title section-gap" }, "Training cohort"),
      h("div", { class: "stat-row", id: "cohort" }, ...tiles.map(([k, v]) => h("div", { class: "stat" }, h("div", { class: "big num" }, v.toLocaleString()), h("div", { class: "lbl" }, k)))));
    if (c.unique_patients_training !== null && c.unique_patients_training !== undefined) box.append(nextCohort(c));
  }
  if (r.runs && r.runs.length) {
    box.append(h("h3", { class: "card-title section-gap" }, "Training runs"),
      h("p", { class: "card-sub" }, "Values logged during training, on training patients only. They are not held-out performance."),
      h("table", { class: "t", id: "train-runs" }, h("thead", {}, h("tr", {}, h("th", {}, "Run"), h("th", {}, "Model"), h("th", {}, "Input"), h("th", { class: "r" }, "Training patients"), h("th", {}, "Training values"))),
        h("tbody", {}, ...r.runs.map((x) => h("tr", {}, h("td", {}, x.run_id), h("td", {}, x.model), h("td", {}, x.input), h("td", { class: "r" }, x.n_train_patients),
          h("td", { class: "muted" }, Object.entries(x.train_metrics).map(([k, v]) => `${k.replaceAll("_", " ")} ${Number.isInteger(v) ? v : f(v, 3)}`).join(" · ") || "–"))))));
  }
  if (r.evaluation) {
    const e = r.evaluation;
    const unc = [e.sd !== null && e.sd !== undefined ? `± ${f(e.sd, 3)} SD` : null, e.ci95 ? `95% CI ${f(e.ci95[0], 3)}–${f(e.ci95[1], 3)}` : null, e.n_folds ? `${e.n_folds} test folds` : null].filter(Boolean).join(" · ");
    box.append(h("div", { class: "eval-panel section-gap", id: "evaluation" },
      h("div", { class: "kicker" }, "Held-out evaluation"),
      h("div", { class: "row", style: { alignItems: "baseline" } }, h("span", { class: "big-metric num" }, f(e.value, 3)), h("span", {}, `${e.metric.replaceAll("_", " ")} on ${e.n_test_patients} held-out patients · ${unc}`)),
      h("p", { class: "muted" }, e.split_description),
      e.comparators.length ? h("table", { class: "t" }, h("thead", {}, h("tr", {}, h("th", {}, "Comparator (same held-out patients)"), h("th", { class: "r" }, e.metric.replaceAll("_", " ")))),
        h("tbody", {}, ...e.comparators.map((c) => h("tr", {}, h("td", {}, c.name), h("td", { class: "r" }, `${f(c.value, 3)}${c.sd !== null && c.sd !== undefined ? ` ± ${f(c.sd, 3)}` : ""}`))))) : null,
      e.p_value_vs_first_comparator !== null && e.p_value_vs_first_comparator !== undefined
        ? h("p", { class: "muted" }, `Difference vs the first comparator: p = ${f(e.p_value_vs_first_comparator, 2)}${e.p_value_vs_first_comparator >= 0.05 ? " (difference uncertain)" : ""}.`) : null));
  }
  if (st.curve_groups && st.curve_groups.length) {
    const el = h("div", { id: "study-curve" });
    box.append(h("h3", { class: "card-title section-gap" }, "Learning curve (held-out, same protocol at every size)"), el);
    requestAnimationFrame(() => curvePlot(el, st.curve_groups.map((g, k) => ({ name: g.model || g.metric, x: g.points.map((p) => p.train_patients),
      y: g.points.map((p) => p.mean), sd: g.points.map((p) => p.sd), color: k === 0 ? T.gold : T.states.A })), st.curve_groups[0].metric));
  }
  return box;
}

function nextCohort(c) {
  const cur = c.unique_patients_training;
  const inp = h("input", { type: "number", min: String(cur + 1), step: "1", value: String(cur * 2 || 10), id: "target-size" });
  const out = h("div", { class: "notice", id: "next-cohort-out" });
  const upd = () => {
    const target = Math.max(0, Math.floor(Number(inp.value) || 0));
    const need = Math.max(0, target - cur);
    if (c.eligible_patients_available !== null && c.eligible_patients_available !== undefined && need > c.eligible_patients_available) {
      out.textContent = `A training cohort of ${target} needs ${need} more patients; ${c.eligible_patients_available} eligible patients are available, so at most ${cur + c.eligible_patients_available} can be reached now.`;
    } else {
      out.textContent = need ? `A training cohort of ${target} needs ${need} more eligible patients (currently ${cur}).` : `The current cohort (${cur}) already reaches ${target}.`;
    }
  };
  inp.oninput = upd; upd();
  return h("div", { class: "section-gap", id: "next-cohort" }, h("h3", { class: "card-title" }, "Next cohort"),
    h("div", { class: "manual" }, h("label", {}, "Target training size (patients)", inp)), h("div", { style: { marginTop: "8px" } }, out),
    h("p", { class: "dim", style: { fontSize: "12.5px" } }, "Counts only: performance at a larger size is not extrapolated."));
}

function curvePlot(el, series, metric, xlabel = "patients used for training") {
  Plotly.newPlot(el, series.map((s, k) => ({ type: "scatter", mode: "lines+markers+text", name: s.name, x: s.x, y: s.y,
    error_y: { type: "data", array: s.sd.map((v) => v ?? 0), visible: s.sd.some((v) => v !== null && v !== undefined), color: s.color, thickness: 1 },
    text: s.y.map((v) => f(v, 3)), textposition: k === 0 ? "top left" : "bottom right", textfont: { color: s.color }, line: { color: s.color, width: 2.5 }, marker: { size: 8, color: s.color } })),
  plotBase({ showlegend: true, legend: { orientation: "h", y: 1.12, font: { color: T.text.primary } }, margin: { l: 56, r: 16, t: 30, b: 46 },
    xaxis: { title: { text: xlabel }, gridcolor: T.surface.raised, tickvals: series[0].x },
    yaxis: { title: { text: metric.replaceAll("_", " ") + " (held out)" }, gridcolor: T.surface.raised } }), { ...plotConfig, displayModeBar: false });
}

// ------------------------------------------------------------------------------------------------ Alzheimer's pilot
function alzPanel(p) {
  const el = h("div", { id: "alz-curve" });
  const counts = Object.entries(p.group_counts).map(([k, v]) => `${v} ${k}`).join(", ");
  const sec = h("section", { class: "separate", id: "alz-pilot" },
    h("div", { class: "card" },
      h("div", { class: "row" }, h("div", { class: "kicker" }, "A separate, completed study"), h("span", { class: "chip chip-green" }, "Completed · held-out results")),
      h("h2", { class: "card-title", style: { fontSize: "20px", marginTop: "6px" } }, p.title),
      h("p", { class: "card-sub" }, `Alzheimer’s disease vs healthy controls on ${p.dataset}. Not epilepsy data. Values read from ${p.source}/.`),
      h("div", { class: "stat-row" },
        h("div", { class: "stat" }, h("div", { class: "big num" }, f(p.seqcnn.mean, 3)), h("div", { class: "lbl" }, `sequence CNN, balanced accuracy on held-out participants (± ${f(p.seqcnn.sd, 3)} SD over folds)`)),
        h("div", { class: "stat" }, h("div", { class: "big num" }, f(p.logreg.mean, 3)), h("div", { class: "lbl" }, `logistic regression on the 24 measures (± ${f(p.logreg.sd, 3)})`)),
        h("div", { class: "stat" }, h("div", { class: "big num" }, p.n_participants), h("div", { class: "lbl" }, `participants (${counts})`)),
        h("div", { class: "stat" }, h("div", { class: "big num" }, p.n_test_folds), h("div", { class: "lbl" }, "held-out test folds"))),
      p.primary_test ? h("p", { class: "muted" }, `Primary test (${p.primary_test.test}): difference ${p.primary_test.diff_mean >= 0 ? "+" : ""}${f(p.primary_test.diff_mean, 3)}, p = ${f(p.primary_test.p, 2)}${p.primary_test.p >= 0.05 ? ": the difference is uncertain; the two approaches performed similarly." : "."}`) : null,
      p.curve.length >= 2 ? [h("h3", { class: "card-title section-gap" }, "Learning curve (same held-out folds at every size)"), el] : null));
  if (p.curve.length >= 2) requestAnimationFrame(() => curvePlot(el, [
    { name: "Sequence CNN", x: p.curve.map((c) => c.train_subjects), y: p.curve.map((c) => c.seqcnn), sd: p.curve.map((c) => c.seqcnn_sd), color: T.gold },
    { name: "Logistic regression (24 measures)", x: p.curve.map((c) => c.train_subjects), y: p.curve.map((c) => c.logreg), sd: p.curve.map((c) => c.logreg_sd), color: T.states.A }], "balanced_accuracy", "participants used for training"));
  return sec;
}
