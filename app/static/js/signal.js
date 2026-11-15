// Waveform + A-D timeline in ONE Plotly figure: both rows share the x axis (seconds in the recording),
// so zoom, pan and the cursor are always in sync. Signal data are fetched for the visible range.
import { api, plotBase, plotConfig, stateScale, STATES, T } from "./util.js";

export class SignalView {
  constructor(el, run, { view = "proc", channels = null, initialSpan = 10, onPick = null, timelineFrac = 0.12, timeline = true, range = null } = {}) {
    this.el = el; this.run = run; this.view = view; this.onPick = onPick;
    this.channels = channels || run.default_view;
    this.span = Math.min(initialSpan, run.t1 - run.t0);
    this.range = range || [run.t0, run.t0 + this.span];
    this.showTimeline = timeline;
    this.spacing = {}; this.cursorI = null; this.highlightSpan = null; this.timelineFrac = timelineFrac;
    this.seq = 0;
  }

  t(i) { return this.run.t0 + i / this.run.fs; }
  index(t) { return Math.max(0, Math.min(this.run.n - 1, Math.round((t - this.run.t0) * this.run.fs))); }

  async init() {
    const r = this.run;
    const times = Array.from({ length: r.n }, (_, i) => this.t(i));
    this.timeline = { type: "heatmap", x: times, y: [0], z: [r.labels], zmin: -0.5, zmax: 3.5, colorscale: stateScale(),
      showscale: false, xaxis: "x", yaxis: "y2", hoverinfo: "none", name: "timeline" };
    const data = await this.fetch(this.range);
    const traces = this.traces(data);
    const layout = this.layout();
    await Plotly.newPlot(this.el, this.allTraces(traces), layout, { ...plotConfig, doubleClick: false });
    this.el.on("plotly_click", (ev) => {
      if (!ev.points || !ev.points.length) return;
      const i = this.index(Number(ev.points[0].x));
      if (this.onPick) this.onPick(i);
    });
    this.el.on("plotly_relayout", (ev) => this.onRelayout(ev));
    this.el.on("plotly_doubleclick", () => false);
  }

  allTraces(tr) {
    const out = this.showTimeline ? [...tr, this.timeline] : [...tr];
    if (this.dots && this.view === "proc") {
      const sp = this.spacing[this.view], n = this.channels.length, x = this.t(this.dots.i);
      out.push({ type: "scatter", mode: "markers", x: this.channels.map(() => x), name: "dots", hoverinfo: "skip", xaxis: "x", yaxis: "y",
        y: this.channels.map((c, k) => this.dots.values[c] + (n - 1 - k) * sp),
        marker: { color: T.gold, size: 11, line: { color: T.surface.inset, width: 2 } } });
    }
    return out;
  }

  // gold dots on every drawn trace at sample i (values: {channel: µV}, processed view only)
  async setDots(i, values) {
    this.dots = values ? { i, values } : null;
    await this.refresh(true);
  }

  async fetch([a, b]) {
    const pad = (b - a) * 0.25;
    const q = new URLSearchParams({ view: this.view, t0: a - pad, t1: b + pad, channels: this.channels.join(",") });
    return api(`/api/runs/${this.run.run_id}/signal?${q}`);
  }

  ensureSpacing(data) {
    if (this.spacing[this.view]) return this.spacing[this.view];
    const spans = Object.values(data.data).map((v) => {
      const s = [...v].sort((p, q) => p - q);
      return s[Math.floor(s.length * 0.98)] - s[Math.floor(s.length * 0.02)];
    }).sort((p, q) => p - q);
    const med = spans[Math.floor(spans.length / 2)] || 50;
    const nice = [10, 20, 25, 30, 40, 50, 60, 75, 100, 150, 200, 250, 300, 400, 500, 1000];
    this.spacing[this.view] = nice.find((x) => x >= med * 0.9) || med;
    return this.spacing[this.view];
  }

  traces(data) {
    const sp = this.ensureSpacing(data);
    const n = this.channels.length;
    return this.channels.map((c, k) => ({
      type: "scattergl", mode: "lines", x: data.t, y: data.data[c].map((v) => v + (n - 1 - k) * sp), name: c,
      line: { color: T.text.primary, width: 1 }, hoverinfo: "none", xaxis: "x", yaxis: "y",
    }));
  }

  layout() {
    const n = this.channels.length, sp = this.spacing[this.view];
    const tf = this.showTimeline ? this.timelineFrac : 0;
    const lay = plotBase({
      margin: { l: 44, r: 10, t: 6, b: 42 }, dragmode: "zoom", hovermode: "x", hoverdistance: -1,
      xaxis: { range: this.range, anchor: this.showTimeline ? "y2" : "y", title: { text: "Time in the recording (s)", standoff: 6 }, gridcolor: T.surface.raised,
        zeroline: false, showspikes: false, tickformat: ".1f", tickfont: { size: 13 } },
      yaxis: { domain: [this.showTimeline ? tf + 0.05 : 0, 1], fixedrange: true, range: [-sp, n * sp], tickvals: this.channels.map((_, k) => (n - 1 - k) * sp),
        ticktext: this.channels, zeroline: false, showgrid: false, tickfont: { color: T.text.primary, size: 13 } },
      yaxis2: { domain: [0, tf], fixedrange: true, showticklabels: true, tickvals: [0], ticktext: ["A–D"], showgrid: false, zeroline: false,
        range: [-0.5, 0.5], tickfont: { color: T.text.primary, size: 13 } },
      shapes: this.shapes(),
      annotations: !this.showTimeline ? [] : STATES.map((s, k) => ({ xref: "paper", yref: "paper", x: 1 - (3 - k) * 0.032, y: tf + 0.012, xanchor: "right", yanchor: "bottom",
        text: `<b>${s}</b>`, showarrow: false, font: { color: T.states[s], size: 14 } })),
    });
    return lay;
  }

  shapes() {
    const out = [];
    if (this.highlightSpan) {
      const [a, b] = this.highlightSpan;
      out.push({ type: "rect", xref: "x", yref: "y2 domain", x0: a, x1: b, y0: -0.25, y1: 1.25, line: { color: T.text.primary, width: 2 }, fillcolor: "rgba(0,0,0,0)", name: "window" });
      out.push({ type: "rect", xref: "x", yref: "y domain", x0: a, x1: b, y0: 0, y1: 1, line: { width: 0 }, fillcolor: "rgba(236,230,218,0.06)", name: "window-wave" });
    }
    if (this.cursorI !== null) {
      const x = this.t(this.cursorI);
      out.push({ type: "line", name: "cursor-wave", xref: "x", yref: "y domain", x0: x, x1: x, y0: 0, y1: 1, line: { color: T.gold, width: 2 } });
      if (this.showTimeline) out.push({ type: "line", name: "cursor-timeline", xref: "x", yref: "y2 domain", x0: x, x1: x, y0: -0.3, y1: 1.3, line: { color: T.gold, width: 3 } });
    }
    return out;
  }

  async onRelayout(ev) {
    let a = ev["xaxis.range[0]"], b = ev["xaxis.range[1]"];
    if (ev["xaxis.range"]) [a, b] = ev["xaxis.range"];
    if (ev["xaxis.autorange"]) { a = this.run.t0; b = this.run.t1; }
    if (a === undefined || b === undefined) return;
    this.range = [Number(a), Number(b)];
    clearTimeout(this._deb);
    this._deb = setTimeout(() => this.refresh(), 120);
  }

  async refresh(resetY = false) {
    const my = ++this.seq;
    const data = await this.fetch(this.range);
    if (my !== this.seq) return;
    const tr = this.traces(data);
    const idx = tr.map((_, k) => k);
    if (resetY || this.el.data.length !== this.allTraces(tr).length) {
      await Plotly.react(this.el, this.allTraces(tr), { ...this.layout(), xaxis: { ...this.layout().xaxis, range: this.range } }, { ...plotConfig, doubleClick: false });
    } else {
      await Plotly.restyle(this.el, { x: tr.map((t) => t.x), y: tr.map((t) => t.y) }, idx);
    }
    this.el.dataset.step = data.step;
  }

  async setView(v) { this.view = v; await this.refresh(true); }
  async setChannels(chs) { this.channels = chs; await this.refresh(true); }

  setCursor(i, { follow = true, span = null } = {}) {
    this.cursorI = i;
    const x = this.t(i);
    const upd = { shapes: this.shapes() };
    if (span || (follow && (x < this.range[0] || x > this.range[1]))) {
      const w = span || this.range[1] - this.range[0];
      this.range = [x - w / 2, x + w / 2];
      upd["xaxis.range"] = this.range;
      Plotly.relayout(this.el, upd).then(() => this.refresh());
      return;
    }
    Plotly.relayout(this.el, upd);
  }

  setHighlight(a, b, { zoom = false } = {}) {
    this.highlightSpan = [a, b];
    const upd = { shapes: this.shapes() };
    if (zoom) { this.range = [Math.max(this.run.t0, a - 3), Math.min(this.run.t1, b + 3)]; upd["xaxis.range"] = this.range; }
    Plotly.relayout(this.el, upd).then(() => zoom && this.refresh());
  }

  cursorShapesX() {
    return (this.el.layout.shapes || []).filter((s) => s.name && s.name.startsWith("cursor")).map((s) => ({ name: s.name, x: s.x0 }));
  }
}
