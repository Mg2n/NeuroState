// Shared helpers. Colours come only from tokens.json (loaded once, then exposed as CSS variables and T).
export let T = null;
export const STATES = ["A", "B", "C", "D"];

export async function loadTokens() {
  T = await (await fetch("/static/tokens.json")).json();
  const r = document.documentElement.style;
  STATES.forEach((s) => r.setProperty(`--state-${s.toLowerCase()}`, T.states[s]));
  r.setProperty("--gold", T.gold);
  r.setProperty("--green", T.green);
  r.setProperty("--text", T.text.primary);
  r.setProperty("--muted", T.text.muted);
  r.setProperty("--dim", T.text.dim);
  r.setProperty("--on-gold", T.text.onGold);
  r.setProperty("--card", T.surface.card);
  r.setProperty("--raised", T.surface.raised);
  r.setProperty("--inset", T.surface.inset);
  r.setProperty("--alt", T.surface.alt);
  r.setProperty("--border", T.border);
  r.setProperty("--border-soft", `color-mix(in srgb, ${T.border} 55%, transparent)`);
  const st = T.background.stops.map(([c, p]) => `${c} ${p * 100}%`).join(", ");
  r.setProperty("--bg-gradient", `radial-gradient(circle at top right, ${st})`);
  r.setProperty("--bg-3", T.background.stops[T.background.stops.length - 1][0]);
  r.setProperty("--sans", `"${T.fonts.sans}"`);
  r.setProperty("--serif", `"${T.fonts.serif}"`);
  r.setProperty("--r-card", T.radius.card);
  r.setProperty("--r-chip", T.radius.chip);
  r.setProperty("--r-pill", T.radius.pill);
  r.setProperty("--pad-card", T.space.card);
  return T;
}

export const stateColor = (k) => T.states[STATES[k]];

export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
export const f = (x, d = 2) => (x === null || x === undefined || Number.isNaN(x) ? "–" : Number(x).toFixed(d));
export const pct = (x, d = 1) => `${f(x, d)}%`;

export async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = `${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch (_) { /* not json */ }
    throw new Error(msg);
  }
  return r.json();
}

export function tex(src, el, display = true) {
  try { katex.render(src, el, { displayMode: display, throwOnError: false, output: "html" }); }
  catch (_) { el.textContent = src; }
  return el;
}

export function plotBase(extra = {}) {
  return {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: `${T.fonts.sans}, sans-serif`, color: T.text.muted, size: 12 },
    margin: { l: 48, r: 12, t: 8, b: 40 }, showlegend: false, ...extra,
  };
}

export const plotConfig = { displaylogo: false, responsive: true, scrollZoom: false,
  modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines", "hoverClosestCartesian", "hoverCompareCartesian"] };

// discrete A-D colour scale for heatmaps holding 0..3
export function stateScale() {
  const c = STATES.map((s) => T.states[s]);
  return [[0, c[0]], [0.25, c[0]], [0.25, c[1]], [0.5, c[1]], [0.5, c[2]], [0.75, c[2]], [0.75, c[3]], [1, c[3]]];
}
