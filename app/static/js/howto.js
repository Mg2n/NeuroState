// One line of real results per step (shown as each step finishes) and the "How it works" panel.
// Formulas follow the code and slide 3 of the deck; the values are this run's own.
import { f, h, pct, STATES, tex } from "./util.js";

const sec = (x) => `${f(x, 3)} s`;

export function summaryLine(id, r) {
  switch (id) {
    case "read": return `${r.recognised}/19 standard channels · ${f(r.sfreq, 0)} Hz · ${f(r.duration_s, 1)} s · ${r.edf_type}`;
    case "segment": return `${sec(r.tmin)}–${sec(r.tmax)} (${f(r.duration_s, 1)} s) · ${({ marker: "from a marker", full: "full recording", manual: "manual" })[r.method]}`;
    case "prepare": return `average reference · 2–20 Hz and 1–40 Hz at ${f(r.sfreq, 0)} Hz · ${r.shape[0]} × ${r.shape[1]}`;
    case "peaks": return `${r.n_used} GFP peaks used (cap ${r.cap})${r.sampled ? `, sampled from ${r.n_local_maxima}` : ""}`;
    case "fit": return `modified k-means · n_init ${r.n_init} · seed ${r.seed} · GEV at peaks ${f(r.gev_peaks, 3)}`;
    case "name": return STATES.map((s) => `${s} |r| ${f(r.abs_r[s], 2)}`).join(" · ");
    case "label": return `${r.n_samples.toLocaleString()} samples · GEV ${f(r.gev_all_samples, 3)} · ${r.min_segment ? `smoothing ${r.min_segment} samples` : "no smoothing"}`;
    case "measures": return `duration, occurrence, coverage for A–D · ${r.n_transitions} transitions`;
    case "cnn": return `${r.n_windows} windows of 4 × 512 · ${r.leftover_samples} samples left over`;
    default: return "";
  }
}

const V = (pairs) => h("div", { class: "vals" }, ...pairs.map(([k, v], i) => [i ? " · " : "", k, " ", h("b", {}, v)]));

export function howTo(id, r) {
  const box = h("div", { class: "howto" });
  const p = (t) => box.append(h("p", { style: { margin: "0 0 4px" } }, t));
  const F = (s) => box.append(tex(s, h("div")));
  switch (id) {
    case "read":
      p("MNE reads the EDF signals and converts them to volts. Channel names are matched to the 19 standard 10–20 electrodes: trailing dots and case are normalised, and T7/T8/P7/P8 become T3/T4/T5/T6 as in the pipeline.");
      box.append(V([["sampling rate", `${f(r.sfreq, 0)} Hz`], ["duration", sec(r.duration_s)], ["channels in file", r.n_channels],
        ["recognised", `${r.recognised}/19`], ["not used", r.not_used.length],
        ["renamed from new names", Object.entries(r.aliases_applied).map(([a, b]) => `${b}→${a}`).join(", ") || "none"]]));
      break;
    case "segment":
      p("The resting segment runs from the first event marker matching “eyes closed” to the next marker. With no such marker the whole recording is used; you can also set the start and end by hand.");
      box.append(V([["start", sec(r.tmin)], ["end", sec(r.tmax)], ["length", sec(r.duration_s)], ["method", r.how],
        ["markers in file", r.markers.length ? r.markers.map((m) => `${m.description} @ ${f(m.onset, 2)} s`).join(", ") : "none"]]));
      if (r.note) box.append(h("p", { class: "muted" }, r.note));
      break;
    case "prepare":
      p("Each electrode is re-expressed relative to the mean of all 19 at the same instant. Two zero-phase FIR band-pass copies are then made and resampled to 128 Hz: 2–20 Hz for microstates, 1–40 Hz for the waveform branch.");
      F(String.raw`v_i^{\mathrm{ref}}(t) = v_i(t) - \frac{1}{N}\sum_{j=1}^{N} v_j(t), \qquad N = 19`);
      box.append(V([["reference", "average of 19"], ["microstate band", "2–20 Hz"], ["second copy", "1–40 Hz"], ["rate", `${f(r.sfreq, 0)} Hz`],
        ["shape", `${r.shape[0]} channels × ${r.shape[1]} samples`], ["length", sec(r.duration_s)]]));
      break;
    case "peaks":
      p("Global field power is the spread of the 19 voltages at one instant. Its local maxima are the moments with the strongest, most stable maps, and they are what the clustering sees.");
      F(String.raw`\mathrm{GFP}(t) = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\big(v_i(t) - \bar v(t)\big)^2}`);
      box.append(V([["GFP maxima found", r.n_local_maxima], ["used", r.n_used], ["cap", r.cap], ["sampling", r.how]]));
      break;
    case "fit":
      p("Modified k-means (Pycrostates) groups the peak maps into four maps, ignoring polarity, and keeps the best of 20 restarts by GEV. GEV is the share of the signal’s variance the maps explain: a measure of map fit, not accuracy.");
      F(String.raw`\mathrm{GEV} = \frac{\sum_t \big(\mathrm{GFP}(t)\, r(t)\big)^2}{\sum_t \mathrm{GFP}(t)^2}`);
      box.append(V([["clusters", r.n_clusters], ["n_init", r.n_init], ["seed", r.seed], ["peaks", r.n_peaks], ["GEV at the peaks", f(r.gev_peaks, 3)]]));
      break;
    case "name":
      p("The four fitted maps are paired one-to-one with the published Koenig 2002 maps (Hungarian assignment) by spatial correlation over the same electrodes, sign ignored. Each fitted map takes the name of its partner.");
      F(String.raw`|r| = \left|\frac{\sum_{i}(x_i-\bar x)(y_i-\bar y)}{\sqrt{\sum_i (x_i-\bar x)^2}\sqrt{\sum_i (y_i-\bar y)^2}}\right|`);
      box.append(V([...STATES.map((s) => [`${s}:`, `|r| = ${f(r.abs_r[s], 3)}`]), ["k-means cluster for A–D", r.cluster_for_ABCD.join(", ")], ["greedy matching", r.note]]));
      break;
    case "label":
      p("Every sample takes the label of the fitted map it correlates with most strongly, ignoring sign. GEV is then computed over every sample of the segment with those labels.");
      F(String.raw`L(t) = \underset{k \in \{A,B,C,D\}}{\arg\max}\; \big|\, r(\mathbf v(t), \mathbf m_k) \big|`);
      box.append(V([["samples labelled", r.n_samples.toLocaleString()], ["GEV over all samples", f(r.gev_all_samples, 3)], ["smoothing", r.smoothing]]));
      break;
    case "measures":
      p("A visit is an unbroken run of one label. Duration, occurrence and coverage summarise each map; transitions count switches from one map to another, with repeats of the same label not counted.");
      F(String.raw`\text{coverage}_k = \frac{\text{samples of }k}{\text{all samples}} \qquad \text{mean duration}_k = \frac{\text{samples of }k}{\text{visits of }k}\cdot\frac{1}{f_s}`);
      F(String.raw`\text{occurrence}_k = \frac{\text{visits of }k}{\text{seconds}} \qquad P(k \to j) = \frac{n_{k\to j}}{\sum_{j' \ne k} n_{k \to j'}}`);
      box.append(V(r.table.map((t) => [`${t.state}:`, `${f(t.mean_duration_ms, 1)} ms, ${f(t.occurrence_per_s, 1)} /s, ${pct(t.coverage_pct)}`]).concat([["transitions", r.n_transitions]])));
      break;
    case "cnn":
      p("The A–D timeline is cut into complete 4-s windows of 512 samples. Each window becomes four rows, one per map, with a 1 where that map is present: the input of the sequence CNN.");
      F(String.raw`X_{k,t} = \begin{cases}1 & L(t) = k\\ 0 & \text{otherwise}\end{cases} \qquad W = \left\lfloor \frac{n}{512} \right\rfloor`);
      box.append(V([["windows", r.n_windows], ["shape", r.window_shape.join(" × ")], ["left over", `${r.leftover_samples} samples (${f(r.leftover_s, 2)} s)`], ["input", r.input]]));
      break;
  }
  return box;
}
