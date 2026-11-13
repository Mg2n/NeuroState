// Router, home screen and presentation mode.
import { renderDemo } from "./demo.js";
import { renderStudy, statusBadge, studyStatus } from "./study.js";
import { api, h, loadTokens, T } from "./util.js";

const ns = (window.__ns = window.__ns || {});
const view = document.getElementById("view");
let STATUS = null;

function route() {
  const r = (location.hash.replace(/^#\/?/, "") || "home").split("?")[0];
  document.querySelectorAll(".nav [data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === r));
  window.scrollTo(0, 0);
  ns.route = r;
  if (r === "demo") return renderDemo(view);
  if (r === "research") return renderStudy(view);
  return renderHome();
}

async function renderHome() {
  view.innerHTML = "";
  const st = await studyStatus();
  view.append(
    h("section", { class: "hero" },
      h("div", { class: "kicker" }, "EEG microstate learning platform"),
      h("h1", {}, "NeuroState"),
      h("p", { class: "lead" }, "From EEG voltages to scalp maps to an A–D microstate timeline."),
      h("p", {}, "NeuroState filters and re-references an EEG, finds four recurring scalp maps, names them A–D against published reference maps, labels every moment of the recording and prepares the sequence input for a neural network.")),
    h("div", { class: "actions" },
      h("section", { class: "card action" },
        h("div", { class: "kicker" }, "Interactive demo"),
        h("h2", {}, "Walk through one EEG"),
        h("p", {}, "One public recording (PhysioNet EEG Motor Movement/Imagery, participant S001, eyes-closed baseline), step by step: preprocessing, GFP peaks, scalp maps, A–D names, the labelled timeline and its measures. Click any moment to see why it got its label."),
        h("div", { class: "seqstrip", "aria-hidden": "true" }, ...["A", "A", "B", "B", "B", "C", "D", "D"].map((s) => h("span", { style: { background: T.states[s] } }, s))),
        h("div", { class: "row" }, h("a", { class: "btn btn-primary", href: "#/demo", id: "open-demo" }, "Start the demo"),
          STATUS && !STATUS.demo_ready ? h("span", { class: "dim", style: { fontSize: "13px" } }, "Bundle not built: run app/tools/fetch_public_inputs.py") : null)),
      h("section", { class: "card action" },
        h("div", { class: "kicker" }, "Lead application"),
        h("h2", {}, "Epilepsy research"),
        h("p", {}, "Process compatible EDF recordings with the real pipeline and get their maps, A–D sequences and measures. See how sequences become CNN input, and the status of the epilepsy CNN."),
        h("div", {}, statusBadge(st)),
        h("div", { class: "row" }, h("a", { class: "btn", href: "#/research", id: "open-study" }, "Open epilepsy research")))));
}

function togglePresent(force) {
  const on = force ?? !document.body.classList.contains("presenting");
  document.body.classList.toggle("presenting", on);
  document.getElementById("present-btn").setAttribute("aria-pressed", on);
  if (on && document.fullscreenEnabled && !document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
  if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
  setTimeout(() => document.querySelectorAll(".js-plotly-plot").forEach((p) => Plotly.Plots.resize(p)), 80);
}
ns.togglePresent = togglePresent;

(async function boot() {
  await loadTokens();
  STATUS = await api("/api/status");
  document.getElementById("present-btn").onclick = () => togglePresent();
  document.addEventListener("keydown", (e) => {
    if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
    if ((e.key === "p" || e.key === "P") && !e.metaKey && !e.ctrlKey && !e.altKey) togglePresent();
  });
  document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && document.body.classList.contains("presenting")) togglePresent(false); });
  window.addEventListener("hashchange", route);
  document.body.classList.remove("loading");
  await route();
  ns.ready = true;
})();
