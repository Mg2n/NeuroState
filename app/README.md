# NeuroState hackathon interface (`app/`)

**Research use only. Not a diagnostic tool.** This folder adds a local web interface on top of the research pipeline in `experiments/`. It does not modify any existing file. It imports `prep`, `microstates`, `validate_microstates`, `run_experiment` and `edf_pipeline_check` unchanged.

There are two flows:

| Flow | What it is | Data |
|---|---|---|
| **Interactive demo** (`#/demo`) | The judge-facing walkthrough of **one fixed recording**, in 8 steps: recording → preprocessing → GFP peaks → four maps → names A–D → every moment labelled (click inspector, **Show an example**) → measures → CNN input | PhysioNet EEGMMIDB S001R02 (public, eyes-closed baseline). Precomputed once with the real pipeline into `app/cache/demo/` and then only read |
| **Epilepsy research** (`#/research`) | Compatible EDFs run through the real pipeline in a background worker, with a plain status and the real outputs: maps, A–D sequence, duration, occurrence, coverage, transitions and a ZIP export. Also covers how sequences become CNN input and the CNN results section | Any compatible EDF you add |

The epilepsy CNN has **not** been trained yet. The CNN results section shows **"Epilepsy training pending"** until a real results file exists (see [After training and evaluation](#3-after-training-and-evaluation-fill-the-epilepsy-page)).

## 1. Setup (once) and launch

Run these from the repository root. Tested with Python 3.12 on Linux.

```bash
python3.12 -m venv experiments/.venv
```

```bash
experiments/.venv/bin/pip install -r app/requirements.txt
```

```bash
git clone https://github.com/Mohammed-T-AlQarni/NeuroState-Microstates.git NeuroState-Microstates
```

```bash
experiments/.venv/bin/python app/tools/fetch_public_inputs.py
```

`app/requirements.txt` includes `experiments/requirements.txt` (MNE 1.13.2, Pycrostates 0.6.1, torch 2.15.0) and adds the web and test packages. The NeuroState-Microstates clone is used unmodified; the repository's `.gitignore` already excludes it.

`fetch_public_inputs.py` needs internet once (physionet.org and github.com). It:
- runs NeuroState-Microstates' own `tools/fetch_public_inputs.py --step physionet --physionet-subject S001`, then checks `S001R02.edf` against PhysioNet's `SHA256SUMS.txt` (`31a95e0a…e847e`, matched);
- gets the Koenig 2002 template. It first tries NeuroState-Microstates' `--step microstatelab-api` and `tools/convert_templates.py`. If `api.github.com` is unreachable (it was here), it does a sparse `git clone` of MICROSTATELAB at the recorded commit `3e142e3`. It checks the git blob SHA-1 and the SHA-256 against NeuroState-Microstates' `docs/data_checksums.csv` (matched), then converts with the same `neurostate.templates` functions, including the second-reader and round-trip checks. The output is `NeuroState-Microstates/templates/Koenig2002_4class.json`, where `validate_microstates.py` expects it;
- builds the demo bundle (`app/tools/build_demo.py` → `app/cache/demo/`).

Launch (after this, no internet is needed):

```bash
app/run.sh
```

It opens http://127.0.0.1:8765/ in your browser. `experiments/.venv/bin/python -m app --port 8765 --no-browser` does the same without opening a browser.

Nothing downloaded or uploaded is committed. `app/cache/` (sample, demo bundle, uploads) is gitignored. The demo bundle stays out of git because it holds EEG signal values and the Koenig maps, whose source repository grants no redistribution licence.

## 2. Demo for the judges

Press **P** or click **Presentation**: full screen, larger plots, fewer controls. Keys **1–8** jump to a step; **← →** move between steps (on step 6 they step one sample).

1. **Run the real sample.** Open *Interactive demo* and walk steps 1–5. Say: *"This is one public EEG, 19 standard electrodes. We average-reference it and filter to 2–20 Hz (step 2). The strongest moments, the GFP peaks, go into clustering (step 3). That gives four recurring scalp maps (step 4), and we name them A–D by matching them one-to-one to the published Koenig 2002 maps; |r| is how well each pair matches (step 5)."* "How it works" on each step shows the formula and this run's values.
2. **Click one EEG moment and explain its label.** On step 6, click anywhere on the waveform or the A–D strip, or press **Show an example**. Say: *"At this instant the 19 voltages form this scalp map. Here is how strongly it correlates with each of this recording's four maps. The best match wins, so this moment is labelled B."* The sentence under the bars is generated from the real values. Raw / Processed switches the trace without moving the cursor.
3. **Open the epilepsy study and show the Example CNN input.** Step 8 shows it, as does *Epilepsy research → Show the example CNN input*. Say: *"The A–D timeline is cut into 4-second windows; each becomes four one-hot rows; that is what the CNN reads. Epilepsy training is pending: the data arrive in a few days."*

## 3. After training and evaluation: fill the epilepsy page

The page reads **`app/study_results/epilepsy/results.json`** at load time. That file does not exist yet, so the page shows the pending state. Its format is the Pydantic model in `app/study_contract.py`, also published as JSON Schema in `app/study_results/schema.json`. An invalid file keeps the pending state and logs the validation error to the server console.

Once `run_experiment.py` has written a results folder (for example `results/epilepsy_seqcnn/` with `results.json`, `fold_metrics.csv`, `oof_predictions.csv`, `val_predictions.csv`, `log.txt`), convert it:

```bash
experiments/.venv/bin/python app/tools/build_study_results.py --run results/epilepsy_seqcnn --study epilepsy --out app/study_results/epilepsy/results.json --labels epilepsy "no epilepsy" --recordings-ingested N --recordings-processed N --eligible-available N
```

- `--recordings-*` and `--eligible-available` are optional. Without them, processed and ingested default to the number of patients in `oof_predictions.csv`, because `run_experiment.load` reads one recording per patient.
- A follow-up summary folder with a `curve/` subfolder, like `results/followup_seqcnn`, is also accepted. It adds the learning curve.
- Restart is not needed: reload the page.

Which field switches on which panel:

| Field in `results.json` | Panel |
|---|---|
| no file / invalid file | "Epilepsy training pending" only |
| `status` | badge: `pending` → "Epilepsy training pending", `training`, `trained` → "model trained · held-out evaluation pending", `evaluated` → "evaluated on held-out patients" |
| `cohort.*` | Training cohort counts |
| `cohort.unique_patients_training` | the Next cohort control (target size minus current, capped by `eligible_patients_available`; no extrapolation of accuracy) |
| `runs[]` | Training runs table, labelled as training values (never held-out) |
| `evaluation` (requires `status: evaluated`) | Held-out evaluation panel: metric ± uncertainty, test patients, split, comparators, p-value |
| `learning_curve[]` | Drawn only for groups with the same model, metric and `evaluation_protocol` at ≥ 2 training sizes |

A file written from training alone (no held-out test yet) should use `status: "trained"` and leave out `evaluation`. The converter sets `evaluated` only when `fold_metrics.csv` and `oof_predictions.csv` (test folds) exist.

## 4. Tests

```bash
NODE_PATH=$(npm root -g) experiments/.venv/bin/python -m pytest app/tests -q
```

Result here: **28 passed** (about 60 s), including **15/15 browser checks**.

| File | What it checks |
|---|---|
| `test_parity.py` | **Inline parity.** The adapter equals the repo functions called step by step, as in `edf_pipeline_check.py`: channels, segment, the `ms`/`dl` arrays, peaks, maps (up to sign), A–D assignment, \|r\|, labels, the 24 features, windows. |
| | **Parity with the reference script.** It runs the unmodified `edf_pipeline_check.main()` on S001R02, with names normalised on read and `--tmin 0 --tmax 61`, and compares `results.json`, `cnn_input_onehot_4x512.npy` and `prepared/*.npz` with the adapter. All are exactly equal, apart from floats at a 1e-12 tolerance. |
| | Channel normalisation and the optional smoothing (`reject_short_segments`). |
| `test_demo_and_api.py` | The demo bundle equals a fresh pipeline run. The demo works with no EDF and the pipeline disabled. Every API number equals the backend arrays. A research job runs the real pipeline. The ZIP contents and manifest are complete. An incompatible upload is refused. |
| `test_incompatible.py` | Fixtures made with MNE: 18 channels (missing Pz), 64 Hz, 3 s, a header shifted by one byte, and EDF+D with a 5-s gap. In the EDF+D case the segment is cut to one continuous stretch and never crosses the gap. Also manual bounds and marker selection. |
| `test_contract.py` | No file → pending. Invalid JSON or schema → pending plus a logged error. Patient IDs are rejected. With and without `evaluation`. A curve with one size or mixed metrics → no chart. The converter on the Alzheimer's outputs and on a `run_experiment.py` folder gives a valid file with values equal to the source. `schema.json` is current. The Alzheimer's panel values equal the files. |
| `test_e2e.py` → `e2e/e2e.js` | Playwright. See the list below. |

The browser test (`e2e/e2e.js`) checks:
- the demo opens from the bundle without any research call, and every step renders;
- three waveform clicks and one timeline click: both cursors land on the same sample, and the inspector's |r| and label equal the backend values;
- the arrow keys step one sample;
- Raw/Processed keeps the cursor time;
- Show an example works;
- the research page with no results file shows "Epilepsy training pending", with no numbers, charts or progress bars in the epilepsy section;
- the phrase "trained on epilepsy" appears nowhere;
- an uploaded S001R02 is processed, and the measures shown equal the backend;
- an incompatible file is refused with its reason;
- the Example CNN input renders;
- a fixture results file shows the cohort, runs, evaluation and curve;
- the presentation mode demo sequence works at 1920×1080;
- there are no page errors.

Screenshots are in `app/screenshots/`. The two that show the Koenig maps (`03_demo_5_name.png`, `07_research_outputs.png`) are regenerated locally by the test and are gitignored.

Check that no research file changed:

```bash
git status --short && git diff --stat main
```

Only `app/` is new.

## 5. Deviations, limitations, things not verified

- **Scope update applied.** The demo is a fixed walkthrough of one bundled recording instead of an "analyze any EEG" screen. Upload-and-process lives on the Epilepsy research page, with a plain job status instead of the step-by-step checklist. The per-step "How it works" panels, with formulas and values, moved into the demo steps.
- **Deck supplied as PDF, not PPTX.** Design tokens (`app/static/tokens.json`) come from the PDF's drawing, text and gradient operators:
  - A–D colours: A #5B8FD9, B #E39A5B, C #5FB27F, D #C46A98 (your estimates were exact);
  - gold #F0B45A; text #ECE6DA; muted text #A9B3BC;
  - cards #1A242D / #26313B; radial background #1C2833 → #121A21 → #0E151B;
  - fonts Inter and Lora, bundled from @fontsource (OFL).
  
  The research code's `COLORS` are not used.
- **Channel names.** `edf_pipeline_check.py` only renames T7/T8/P7/P8. It does **not** strip EEGMMIDB's trailing dots or fix case; that is done in the app layer (`normalise_name`).
- **No-marker fallback.** `edf_pipeline_check.resting_segment` stops when no marker matches. The app catches that and analyses the full recording, saying so on screen. S001R02 has only a `T0` marker, so it uses the full 61 s.
- **EDF+D.** Gaps are found with NeuroState-Microstates' own readers (`neurostate.io_edf`). Annotations are re-timed as its `load_edf` does. The analysis uses the longest continuous stretch inside the chosen span, with a notice; filtering never crosses a junction. This was tested on a synthetic EDF+D, not on the Zenodo files.
- **Sampling-rate rule.** Files must be above 80 Hz, because the pipeline also makes the 1–40 Hz copy. The 2–20 Hz band alone would only need more than 40 Hz.
- **Single-recording maps.** In the demo and in research processing, maps are fitted on the single recording, as in `edf_pipeline_check.py`. In a study they must come from the training patients of each fold (`run_experiment.py`).
- **Numbers will differ from the deck.** This pipeline resamples to 128 Hz, so its numbers differ from the deck's "Run 1" (160 Hz, NeuroState-Microstates). For example, here there are 1260 GFP peaks, |r| 0.889/0.918/0.917/0.900, and GEV 0.799 at the peaks / 0.722 over all samples. No deck figure is in the code.
- **Example moment.** "Show an example" uses sample 3834 (29.95 s, label B). It is picked deterministically by `pipeline_adapter.pick_example`: the GFP peak in the first 30 s with the widest |r| margin.
- **Public epilepsy inventory not shown.** The deck's inventory (73 datasets, TUEP …) exists only in the deck, not as data in the repo. Following "no numbers copied from the deck", the panel "Public data identified (separate from the training cohort)" is not shown. Add a data file to the repo if you want it.
- **Converter conventions.** `created` comes from a run's `results.json`. `run_experiment.py` outputs do not record one, so their runs show "not recorded in results.json". The converter's `train_metrics` are mean epochs trained and the inner early-stopping balanced accuracy, both from training-fold patients only.
- **Not verified.** Windows/macOS launch (tested on Linux only). Real clinical EDFs. Large recordings: plotting fetches only the visible window, but the A–D strip and GFP arrays are sent whole. Fullscreen in a real (non-headless) browser.
- **Torch build.** Installed from PyPI (CUDA build), because download.pytorch.org was blocked here. The version matches the pin (2.15.0).
