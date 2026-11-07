"""Task 08: build the paper (submission/NeuroState_paper.docx) on the IEEE conference template, from saved results.

Numbers are read from results/ and figures/paper/, never typed. The exceptions are facts about other people's work
(published values, in the text below and in make_figures.LITERATURE). Yellow text marks what the team must still fill in.

  .venv/bin/python make_paper.py
"""
import io
import json
import os
import re
import zipfile

import docx
import pandas as pd
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, Twips

R, FIG, SUB = "../results", "../figures/paper", "../submission"
TEMPLATE = os.path.join(SUB, "ieee_conference_template_a4.docx")
STRICT = (("http://purl.oclc.org/ooxml/wordprocessingml/main", "http://schemas.openxmlformats.org/wordprocessingml/2006/main"),
          ("http://purl.oclc.org/ooxml/officeDocument/relationships", "http://schemas.openxmlformats.org/officeDocument/2006/relationships"),
          ("http://purl.oclc.org/ooxml/officeDocument/math", "http://schemas.openxmlformats.org/officeDocument/2006/math"),
          ("http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing", "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"),
          ("http://purl.oclc.org/ooxml/drawingml/main", "http://schemas.openxmlformats.org/drawingml/2006/main"),
          ("http://purl.oclc.org/ooxml/drawingml/picture", "http://schemas.openxmlformats.org/drawingml/2006/picture"),
          ("http://purl.oclc.org/ooxml/officeDocument/extendedProperties", "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"),
          ("http://purl.oclc.org/ooxml/officeDocument/docPropsVTypes", "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"),
          (' w:conformance="strict"', ""), (' conformance="strict"', ""))
REFS = {
    "lecun": 'Y. LeCun, Y. Bengio, and G. Hinton, "Deep learning," Nature, vol. 521, no. 7553, pp. 436-444, 2015, doi: 10.1038/nature14539.',
    "lawhern": 'V. J. Lawhern, A. J. Solon, N. R. Waytowich, S. M. Gordon, C. P. Hung, and B. J. Lance, "EEGNet: a compact convolutional neural network for EEG-based brain-computer interfaces," J. Neural Eng., vol. 15, no. 5, art. 056013, 2018, doi: 10.1088/1741-2552/aace8c.',
    "data": 'A. Miltiadous et al., "A dataset of scalp EEG recordings of Alzheimer\'s disease, frontotemporal dementia and healthy subjects from routine EEG," Data, vol. 8, no. 6, art. 95, 2023, doi: 10.3390/data8060095.',
    "michel": 'C. M. Michel and T. Koenig, "EEG microstates as a tool for studying the temporal dynamics of whole-brain neuronal networks: A review," NeuroImage, vol. 180, pp. 577-593, 2018, doi: 10.1016/j.neuroimage.2017.11.062.',
    "koenig": 'T. Koenig et al., "Millisecond by millisecond, year by year: Normative EEG microstates and developmental stages," NeuroImage, vol. 16, no. 1, pp. 41-48, 2002, doi: 10.1006/nimg.2002.1070.',
    "dice": 'A. Miltiadous, E. Gionanidis, K. D. Tzimourta, N. Giannakeas, and A. T. Tzallas, "DICE-Net: A novel convolution-transformer architecture for Alzheimer detection in EEG signals," IEEE Access, vol. 11, pp. 71840-71858, 2023, doi: 10.1109/ACCESS.2023.3294618.',
    "adformer": 'Y. Wang, N. Mammone, D. Petrovsky, A. T. Tzallas, F. C. Morabito, and X. Zhang, "ADformer: A multi-granularity spatial-temporal transformer for EEG-based Alzheimer detection," arXiv:2409.00032v2, 2025.',
    "jiang": 'L. Jiang, Y. Chen, Y. He, J. Liang, X. Zhao, and X. Guo, "A two-stage EEG microstate fusion framework for dementia screening and Alzheimer\'s disease/frontotemporal dementia differentiation," Biosensors, vol. 16, no. 5, art. 258, 2026, doi: 10.3390/bios16050258.',
    "brookshire": 'G. Brookshire et al., "Data leakage in deep learning studies of translational EEG," Front. Neurosci., vol. 18, art. 1373515, 2024, doi: 10.3389/fnins.2024.1373515.',
    "nadeau": 'C. Nadeau and Y. Bengio, "Inference for the generalization error," Mach. Learn., vol. 52, no. 3, pp. 239-281, 2003, doi: 10.1023/A:1024068626366.',
    "pycro": 'V. Férat, M. Scheltienne, D. Brunet, T. Ros, and C. Michel, "Pycrostates: a Python library to study EEG microstates," J. Open Source Softw., vol. 7, no. 78, art. 4564, 2022, doi: 10.21105/joss.04564.',
    "mne": 'A. Gramfort et al., "MEG and EEG data analysis with MNE-Python," Front. Neurosci., vol. 7, art. 267, 2013, doi: 10.3389/fnins.2013.00267.',
    "ns": '[[M. FAMILY-NAME (full name needed)]], "NeuroState-Microstates: an explainable EEG-to-microstates research tool," version 0.1.0, 2026. [Online]. Available: https://github.com/Mohammed-T-AlQarni/NeuroState-Microstates',
}
order = []


def cite(*keys):
    for k in keys:
        if k not in order:
            order.append(k)
    return "[" + ", ".join(str(order.index(k) + 1) for k in keys) + "]"


def load_template():
    """The IEEE template is saved as Strict Open XML, which python-docx cannot read: map it to the transitional names."""
    src, buf = zipfile.ZipFile(TEMPLATE), io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.namelist():
            data = src.read(item)
            if item.endswith((".xml", ".rels")):
                text = data.decode("utf8")
                for a, b in STRICT:
                    text = text.replace(a, b)
                data = text.encode("utf8")
            out.writestr(item, data)
    buf.seek(0)
    d = docx.Document(buf)
    body = d.element.body
    for el in list(body):
        body.remove(el)
    body.append(OxmlElement("w:sectPr"))
    return d


class Paper:
    def __init__(self):
        self.d = load_template()
        s = self.d.sections[0]
        self.page(s, 1)
        s.top_margin = Pt(54)

    def page(self, s, cols):
        s.page_width, s.page_height = Twips(11906), Twips(16838)
        s.left_margin = s.right_margin = Pt(45.35)
        s.top_margin, s.bottom_margin = Pt(54), Pt(72)
        s.header_distance = s.footer_distance = Pt(36)
        s.gutter = Pt(0)
        el = s._sectPr.find(qn("w:cols"))
        if el is None:
            el = OxmlElement("w:cols")
            s._sectPr.append(el)
        el.set(qn("w:num"), str(cols))
        el.set(qn("w:space"), "360")

    def columns(self, n):
        self.page(self.d.add_section(WD_SECTION.CONTINUOUS), n)

    def new_page(self, n):
        """Section that always starts on a new page: a full-width block placed here can never run across a page."""
        self.page(self.d.add_section(WD_SECTION.NEW_PAGE), n)

    def text(self, p, s):
        """[[...]] = yellow, for the team to fill in."""
        for i, part in enumerate(re.split(r"\[\[(.*?)\]\]", s)):
            if part:
                r = p.add_run(part)
                if i % 2:
                    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        return p

    def p(self, s, style="Body Text"):
        return self.text(self.d.add_paragraph(style=style), s)

    def lead(self, head, s):
        """Body paragraph with an italic run-in heading."""
        p = self.d.add_paragraph(style="Body Text")
        p.add_run(f"{head}. ").italic = True
        return self.text(p, s)

    def h1(self, s):
        self.d.add_paragraph(s, style="Heading 1")

    def h2(self, s):
        self.d.add_paragraph(s, style="Heading 2")

    def bullets(self, items):
        for s in items:
            self.p(s, "bullet list")

    def figure(self, name, caption, wide=False, width=3.3):
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(os.path.join(FIG, f"{name}.png"), width=Inches(6.9 if wide else width))
        self.d.add_paragraph(caption, style="figure caption")

    def table(self, name, caption, widths):
        """Same rows as figures/paper/<name>.md. Widths in inches: written to tblW, tblGrid and every cell, with a fixed
        layout, so Word and LibreOffice agree. Rows stay together and with the caption. Text columns are left-aligned;
        columns holding only numbers are centred."""
        rows = [[c.strip().replace("`", "") for c in ln.strip().strip("|").split("|")]
                for ln in open(os.path.join(FIG, f"{name}.md")) if ln.startswith("|")]
        rows = [rows[0]] + rows[2:]
        numeric = [all(re.fullmatch(r"[\d\s.,±+\-()\[\]/e]+", r[j]) for r in rows[1:]) for j in range(len(rows[0]))]
        cap = self.d.add_paragraph(caption, style="table head")
        cap.paragraph_format.keep_with_next = True
        t = self.d.add_table(len(rows), len(rows[0]))
        t.autofit = False
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        tw = [round(w * 1440) for w in widths]
        cols = int(self.d.sections[-1]._sectPr.find(qn("w:cols")).get(qn("w:num")))
        assert sum(tw) <= (10080 if cols == 1 else 4866), (name, sum(tw) / 1440)  # 7.0 in full width, 3.38 in column
        tp = t._tbl.tblPr
        tblw = tp.find(qn("w:tblW"))
        tblw.set(qn("w:type"), "dxa"), tblw.set(qn("w:w"), str(sum(tw)))
        for j, w in enumerate(tw):
            t.columns[j].width = Twips(w)
        b = OxmlElement("w:tblBorders")
        for side in ("top", "bottom", "insideH"):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single"), e.set(qn("w:sz"), "4"), e.set(qn("w:color"), "000000"), e.set(qn("w:space"), "0")
            b.append(e)
        anchor = next((c for c in tp if c.tag in (qn("w:tblLayout"), qn("w:tblCellMar"), qn("w:tblLook"))), None)
        tp.append(b) if anchor is None else anchor.addprevious(b)
        mar = OxmlElement("w:tblCellMar")
        for side in ("left", "right"):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:w"), "43"), e.set(qn("w:type"), "dxa")
            mar.append(e)
        look = tp.find(qn("w:tblLook"))
        tp.append(mar) if look is None else look.addprevious(mar)
        for i, row in enumerate(rows):
            t.rows[i]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for j, val in enumerate(row):
                c = t.cell(i, j)
                c.width = Twips(tw[j])
                c.paragraphs[0].style = self.d.styles["table col head" if i == 0 else "table copy"]
                c.paragraphs[0].paragraph_format.keep_with_next = i < len(rows) - 1
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if numeric[j] else WD_ALIGN_PARAGRAPH.LEFT
                c.paragraphs[0].add_run(val).font.size = Pt(7.5)
        sp = self.d.add_paragraph(style="Body Text")
        sp.paragraph_format.space_after = Pt(4)


def main():
    conf = json.load(open(f"{R}/confirmation/results.json"))
    M, Cmp = conf["models"], conf["comparisons"]
    F, H, E, L, RFM = "fusion_eegnet_ens5_logreg", "hybrid_ens5", "eegnet_ens5", "baseline_logreg", "baseline_rf"
    ba = lambda m: f"{M[m]['balanced_accuracy']['mean']:.3f}"
    pa = lambda m: f"{M[m]['pooled_auc']['point']:.3f}"
    ci = lambda m: "[{:.3f}, {:.3f}]".format(*M[m]["pooled_auc"]["ci95"])
    d = lambda a, b, k="balanced_accuracy": Cmp[f"{a}_vs_{b}_{k}"]["diff_mean"]
    pv = lambda a, b, k="balanced_accuracy": Cmp[f"{a}_vs_{b}_{k}"]["corrected_p"]
    early = lambda m: conf["context"][m]["balanced_accuracy_earlier"]
    t5 = json.load(open(f"{R}/main_AD_vs_HC/results.json"))
    leak = t5["leakage_demo_eegnet_window_split"]
    f5 = pd.read_csv(f"{R}/main_AD_vs_HC/fold_metrics.csv")
    t5m = lambda m, k="balanced_accuracy": f5[f5.model == m][k].mean()
    from improve_analysis import paired
    h5 = paired(f5.assign(), "hybrid", "eegnet", "balanced_accuracy")
    c3 = pd.read_csv(f"{R}/improve_3class/fold_metrics.csv")
    c3m = lambda m: f"{c3[c3.model == m].balanced_accuracy.mean():.3f}"
    s3 = json.load(open(f"{R}/improve_3class_no086/results.json"))["stats"]
    s3f = json.load(open(f"{R}/improve_3class/results.json"))["stats"]
    prep = open(f"{R}/prep_report.md").read()
    theta = re.search(r"theta 4-8 Hz \| ([\d.]+) ± [\d.]+ \| ([\d.]+) ±", prep).groups()
    alpha = re.search(r"alpha 8-13 Hz \| ([\d.]+) ± [\d.]+ \| ([\d.]+) ±", prep).groups()
    val = open(f"{R}/microstate_validation.md").read()
    gmaps = json.load(open(f"{R}/microstates/group_maps.json"))
    ns_lo, ns_hi = re.search(r"ours_individual vs ns_500 ([\d.]+)-([\d.]+)", val).groups()
    r_all = [float(x) for x in re.findall(r"^\| M\d \| [A-D] \| ([\d.]+) \|", val, flags=re.M)]
    cfg = conf["config"]
    mins = sum(conf["minutes_per_seed"])
    ver = conf["_environment"]["libraries"]
    fu = json.load(open(f"{R}/followup_seqcnn/results.json"))
    fm, fc, ft1 = fu["models"], fu["curve"], next(t for t in fu["tests"] if t["test"] == 1)
    fba = lambda m: f"{fm[m]['balanced_accuracy']['mean']:.3f}"
    fmean = lambda m, k: f"{fm[m][k]['mean']:.3f}"
    ft = lambda n: next(t for t in fu["tests"] if t["test"] == n)
    fd = lambda n: f"{ft(n)['diff_mean']:+.3f}"
    fp = lambda n: f"{ft(n)['corrected_p']:.2f}"
    fdiff = lambda k, n: f"{fc[f'{k}_{n}']['diff']:+.3f}"
    SEQ_, LOG_ = "seqcnn_onehot", "logreg"
    assert all(abs(fc[f"{k}_{n}"]["diff"]) < fc[f"{k}_{n}"]["diff_sd"] for k in ("balanced_accuracy", "auc") for n in (20, 35, 52))
    assert not any(t["corrected_p"] < 0.05 for t in fu["tests"]) and not fu["seqcnn_wins_primary"]
    assert fm["logreg"]["auc"]["mean"] > fm["seqcnn_onehot"]["auc"]["mean"]  # "logistic regression ahead on AUC"
    assert fu["sanity"].endswith("same test subjects True; largest probability difference 0.0.")
    visits = open(f"{R}/followup_seqcnn/visit_lengths.md").read()
    visit = lambda g: [float(x) for x in re.search(rf"^\| {g} \| \d+ \| ([\d.]+) ± [\d.]+ \| ([\d.]+) ± [\d.]+ \| [\d.]+ ± [\d.]+ \| ([\d.]+) ±", visits, flags=re.M).groups()]
    (ad_n, ad_ms, ad_sm), (hc_n, hc_ms, hc_sm) = visit("AD"), visit("HC")
    min_seg = json.load(open(f"{R}/followup_seqcnn/smooth_seed0/results.json"))["_config"]["min_segment"]
    min_ms = min_seg * 1000 / 128
    from models import MicroStateNet
    seq_params = sum(p.numel() for p in MicroStateNet(use_eeg=False).parameters())

    P = Paper()
    P.p("Do EEG Microstates Improve EEGNet? A Preregistered Subject-Wise Comparison for Alzheimer's Disease Classification", "paper title")
    P.p("[[Team Leader Name, Student ID]], [[Team Member 2 Name, Student ID]], [[Team Member 3 Name, Student ID]]", "Author")
    P.p("[[Department, University, City, Country. Group No.]]", "Author")
    P.columns(2)

    P.p(f"Abstract—Resting-state EEG is a low-cost signal for research on Alzheimer's disease (AD), but deep learning results are often inflated by evaluation that lets the same person appear in training and test data. We asked whether EEG microstate information improves a compact raw-EEG network, EEGNet, under strict subject-wise evaluation. We compared EEGNet, a 24-feature microstate baseline, a new hybrid network with an added microstate branch, and a decision-level fusion of EEGNet and the baseline on 65 subjects (36 AD, 29 healthy controls) from the public ds004504 dataset. After exploratory work, we fixed three models and the analysis in advance and tested them on new cross-validation splits. Balanced accuracy was {ba(F)} for late fusion, {ba(E)} for the EEGNet ensemble and {ba(H)} for the hybrid ensemble. No preregistered comparison was significant on a corrected resampled t-test (hybrid vs EEGNet {d(H, E):+.3f}, p = {pv(H, E):.2f}; fusion vs EEGNet {d(F, E):+.3f}, p = {pv(F, E):.2f}). Putting microstates inside the network gave no measurable gain. A random window split raised EEGNet balanced accuracy from {t5m('eegnet'):.3f} (subject-wise, same run) to {leak['balanced_accuracy']:.3f}, showing the size of subject leakage. This work is research only and is not a diagnostic test.", "Abstract")
    P.p("Keywords—EEG, Alzheimer's disease, deep learning, EEGNet, microstates, data leakage, preregistration", "Keywords")

    P.h1("Introduction")
    P.p(f"Deep learning trains many-layered neural networks that learn features directly from data, and it has changed fields such as computer vision, speech recognition and language processing {cite('lecun')}. Its use on medical signals is attractive because expert feature design may not be needed. Public data platforms make such work possible for student teams. Kaggle.com is the best known of these, with shared datasets, notebooks and competitions. For this project the course coordinator approved a non-Kaggle source, OpenNeuro, because it holds a suitable open EEG dataset in a standard format.")
    P.p(f"The purpose of this project is to develop and train a deep learning model that classifies AD vs healthy controls (HC) from resting-state EEG. EEG is non-invasive and cheap to record, and microstates are a compact description of it: brief scalp voltage patterns that repeat over time {cite('michel', 'koenig')}. EEGNet is a compact network designed for EEG {cite('lawhern')}. Whether adding microstate information to such a network helps is an open, testable question.")
    P.p(f"Evaluation is the central difficulty. Brookshire et al. re-used a published CNN on a different cohort, 49 subjects with dementia due to Alzheimer's disease and 49 with subjective cognitive impairment, and found 99.8% test accuracy when segments from one person could fall in both training and test sets, but 53.0% when subjects were kept apart {cite('brookshire')}. Comparing many variants on the same splits creates a second risk: the best row may simply be lucky.")
    P.p(f"On the dataset used here, DICE-Net reports 83.28% accuracy for AD vs HC with leave-one-subject-out (LOSO) validation, using band-power and coherence features {cite('dice')}. ADformer reports 92.82% subject-level F1 for AD vs HC under subject-independent evaluation {cite('adformer')}. A two-stage microstate fusion framework reports 74.3% balanced accuracy for dementia (AD + FTD) vs HC and 63.9% for three classes, under LOSO {cite('jiang')}.")
    P.p("Our contributions are: (1) a hybrid EEGNet with a microstate branch, with maps fitted on training subjects only; (2) a direct, subject-wise comparison with EEGNet and a microstate-only baseline; (3) a preregistered confirmation run on new splits, so that headline numbers are not chosen from the variants explored; and (4) a measured leakage demonstration on the same data and network.")

    P.h1("Project Goals and Objectives")
    P.p("The research question is: do EEG microstate features improve a compact raw-EEG CNN for AD vs HC classification under strict subject-wise evaluation? The objectives were:")
    P.bullets(["Use one public dataset, with all subjects and windows kept, and record settings, seeds and library versions with every result.",
               "Keep every subject in only one side of each split. Fit microstate maps and choose early-stopping subjects from training folds only.",
               "Compare the baseline, EEGNet and the hybrid. Report every result, including when the hybrid does not win.",
               "Fix the final models and analysis before running them on unused splits, and treat those numbers as the headline results.",
               "Measure how much subject leakage would inflate the result."])
    P.p("No target accuracy was set in advance: the goal is an honest answer to the research question, not a particular score.")

    P.h1("Data Acquisition and Preprocessing")
    P.h2("Dataset")
    P.p(f"We used OpenNeuro ds004504 v1.0.9 (CC0) {cite('data')}: eyes-closed resting EEG from 88 people (36 AD, 23 frontotemporal dementia (FTD), 29 HC), recorded on 19 scalp electrodes at 500 Hz. Its authors already applied a 0.5-45 Hz band-pass filter, artifact subspace reconstruction and independent component analysis, and we used these derivatives. The main task uses the 65 AD and HC subjects. All 88 appear in a secondary three-class task.")
    P.h2("Preprocessing")
    P.p(f"Using MNE-Python {cite('mne')}, each recording was set to a fixed channel order and average reference. Two copies were then made and resampled to 128 Hz: 1-40 Hz for EEGNet and 2-20 Hz for microstates. All 88 subjects passed the checks. No amplitude-based rejection was added, because the data are already cleaned and a threshold would be one more tunable choice. Eight subjects therefore keep isolated large transients, and one FTD subject (sub-086) has about four times the median amplitude. As an expected sanity check, relative theta power was higher in AD than HC ({theta[0]} vs {theta[1]}) and relative alpha power lower ({alpha[0]} vs {alpha[1]}).")
    P.h2("Microstates")
    P.p(f"Four maps were fitted with modified k-means from Pycrostates {cite('pycro')} on global field power peaks pooled from the training subjects of each fold. Every sample was then correlated with each map. This gives a 4 × time |correlation| sequence for the hybrid, and 24 features per subject (coverage, duration and occurrence per state, plus 12 transition probabilities) for the baseline. Labels are the best-matching map at every sample, with no temporal smoothing or minimum-segment rule, so visits are short (group means about {hc_ms:.0f}-{ad_ms:.0f} ms, or {hc_n:.1f}-{ad_n:.1f} samples at 128 Hz); conventional pipelines merge short segments and report about 60-120 ms {cite('michel')}. We validated this step separately. Group maps matched the published Koenig A-D maps {cite('koenig')} with |r| from {min(r_all):.2f} to {max(r_all):.2f} (Fig. 5), and our code matched NeuroState-Microstates {cite('ns')}, our own previously released open-source tool, used unmodified for validation, on two subjects with minimum |r| {ns_lo}-{ns_hi}.")

    P.h1("Model Development and Training")
    P.h2("Models")
    P.p(f"A. Baseline: the 24 microstate features with logistic regression or a random forest. B. EEGNet {cite('lawhern')}, re-implemented in PyTorch, on 4-s windows (19 channels × 512 samples). C. Hybrid (ours): the EEGNet branch plus a small 1-D CNN on the |correlation| sequence, with both outputs concatenated before a linear classifier (Fig. 1). Late fusion takes the mean of the EEGNet and logistic-regression probabilities, with 0.5/0.5 weights fixed in advance.")
    P.columns(1)
    P.figure("fig1_architecture", "The hybrid model. EEGNet alone uses only the top branch, with its 256 units going directly to the classifier.", wide=True)
    P.columns(2)
    P.h2("Training")
    P.p(f"Networks used Adam (learning rate {cfg['lr']}, weight decay {cfg['wd']}), a cosine learning-rate schedule, class-weighted cross-entropy and dropout {cfg['dropout']}, for at most {cfg['epochs']} epochs with early stopping (patience {cfg['patience']}). Stopping used 15% of the training subjects as validation. Augmentation was {cfg['crops']} random 4-s crops per subject per epoch, amplitude jitter and small Gaussian noise. A subject's score is the mean of its window probabilities, and the threshold is 0.5. An ensemble averages subject probabilities over 5 network seeds.")
    P.h2("Evaluation Design")
    P.p(f"All evaluation used 5-fold subject-wise stratified cross-validation repeated 3 times. Work proceeded in three stages. First, the planned experiment ran on repeat seeds 0-2. Second, exploratory variants used those same splits; any setting they selected was chosen inside training subjects only. Third, before any run, we wrote down three models, their settings and the analysis, with hashes of the code, and ran them on repeat seeds 3-5, which no earlier result had used. Only this third stage gives the headline numbers. Paired comparisons use the Nadeau-Bengio corrected resampled t-test {cite('nadeau')} because folds share training subjects. Balanced accuracy is the primary metric, giving 3 primary tests and 6 secondary ones. The p values are unadjusted.")

    P.h1("Evaluation and Analysis")
    P.h2("Preregistered Confirmation Results")
    P.p(f"Table I gives the headline results and Table II the comparisons. No comparison reached p < 0.05. The hybrid did not beat EEGNet ({d(H, E):+.3f}, p = {pv(H, E):.2f}), and it had the lowest mean balanced accuracy of the five rows. Late fusion had the highest mean ({ba(F)}), but this run does not show it to be better than EEGNet ({d(F, E):+.3f}, p = {pv(F, E):.2f}) or the hybrid ({d(F, H):+.3f}, p = {pv(F, H):.2f}). Fusion vs logistic regression was not preregistered and is not tested; its balanced accuracy was {ba(F)} vs {ba(L)}, and its pooled AUC almost the same ({pa(F)} vs {pa(L)}).")
    P.columns(1)
    P.table("table1_main_results", "Headline results: preregistered confirmation run (65 subjects, repeat seeds 3-5, 15 folds, threshold 0.5). Mean ± SD over folds", [2.1, 0.85, 0.85, 0.85, 1.2, 0.5, 0.5])
    P.columns(2)
    P.table("table2_comparisons", "Preregistered comparisons (corrected resampled t-test, two-sided, unadjusted)", [1.05, 0.78, 0.7, 0.52, 0.3])
    P.figure("fig2_roc", "ROC curves: mean of the per-repeat curves, confirmation run.", width=2.9)
    P.figure("fig3_confusion", "Subject-level confusion matrices at threshold 0.5, counts over 3 repeats (65 subjects × 3 = 195 predictions, not 195 people).")
    P.p(f"Fig. 2 shows the ranking performance. Confidence intervals overlap widely: pooled AUC was {pa(F)} {ci(F)} for fusion, {pa(E)} {ci(E)} for EEGNet and {pa(H)} {ci(H)} for the hybrid. Fig. 3 shows the errors. The hybrid missed the most AD subjects (pooled sensitivity {M[H]['pooled_sensitivity']:.3f}, vs {M[E]['pooled_sensitivity']:.3f} for EEGNet), while fusion had the highest specificity ({M[F]['pooled_specificity']:.3f}).")
    P.p(f"The earlier splits show how much numbers move. From repeats 0-2 to repeats 3-5, balanced accuracy changed from {early(F):.3f} to {ba(F)} for fusion, {early(H):.3f} to {ba(H)} for the hybrid and {early(E):.3f} to {ba(E)} for EEGNet. The hybrid's earlier lead over EEGNet ({early(H) - early(E):+.3f}) therefore reversed.")
    P.h2("Comparison with Published Work")
    P.p("Table III places these results in context. It is not a ranking: metrics, class definitions and protocols differ. LOSO also trains on 64 AD vs HC subjects per fold, compared with 52 here.")
    P.table("table3_literature", "Published results and this study", [1.15, 0.85, 1.35])
    P.h2("Leakage Demonstration")
    P.p(f"Fig. 4 repeats EEGNet with 4-s windows split at random, so the same people appear in training and test data. Balanced accuracy rose to {leak['balanced_accuracy']:.3f} (AUC {leak['auc']:.3f}, {leak['n_test_windows']:,} test windows), against {t5m('eegnet'):.3f} for subject-wise evaluation in the same planned run (CPU, one seed). That subject-wise value was a single run. It lies above all five seeds later run on Apple MPS on the same splits, for reasons we could not explain, and the headline EEGNet ensemble is {ba(E)}, so the gap shown is on the small side.")
    P.figure("fig4_leakage", "EEGNet under a random window split and under subject-wise cross-validation (same run; error bar = SD over 15 folds).", width=2.9)
    P.h2("Exploratory Variants")
    P.p(f"Table IV lists the exploratory rows on repeat seeds 0-2: inner-validation thresholds, seed ensembles, 8-s windows, other microstate inputs and nested-CV regularisation. None reached significance on the corrected test against its comparator. These rows are not headline results, because with this many variants on the same 65 subjects the best row is expected to look better by chance. In the planned first run, the hybrid vs EEGNet difference was {h5['diff_mean']:+.3f} (p = {h5['corrected_p']:.2f}).")
    P.columns(1)
    P.table("table4_improvements", "Exploratory variants on repeat seeds 0-2. None is a headline result; p = corrected resampled t-test", [2.65, 1.05, 1.05, 1.55, 0.7])
    P.columns(2)
    P.p("A separately preregistered follow-up on the confirmation splits is reported in the Follow-up: Methods and Follow-up: Results subsections below.")
    P.h2("Secondary Task: AD vs FTD vs HC")
    P.p(f"With all 88 subjects and settings fixed in advance, models scored about the same (Table V; chance = 0.333). The hybrid ensemble ({c3m(H)}) did not differ from the EEGNet ensemble ({c3m(E)}; p = {s3f[f'{H}_vs_{E}_balanced_accuracy']['corrected_p']:.2f}). Removing sub-086 changed no model significantly, although logistic regression moved from the lowest of the four to the highest ({s3[f'{L}_vs_with086_balanced_accuracy']['diff_mean']:+.3f}, p = {s3[f'{L}_vs_with086_balanced_accuracy']['corrected_p']:.2f}), so their order should not be read as a ranking. These runs used repeat seeds 0-2 and were not part of the confirmation run.")
    P.columns(1)
    P.table("table5_three_class", "Secondary task. The full cohort is the main result; the sub-086 exclusion is a sensitivity analysis. Effect compares identical test subjects", [1.9, 1.0, 1.0, 1.0, 1.15, 0.95])
    P.columns(2)
    P.h2("Microstate Maps and Features")
    P.p(f"Figs. 5 and 6 and Table VI describe the maps and the AD vs HC differences. Group maps here were fitted on all AD and HC subjects, for validation and description only; classification refits maps on each training fold. The state labels are provisional matches. With these unsmoothed labels, AD subjects showed longer states and lower occurrence on average. With a {min_seg}-sample ({min_ms:.0f} ms) minimum-segment rule, the mean visit becomes {ad_sm:.0f} ms in AD vs {hc_sm:.0f} ms in HC (maps from the training folds), so the direction of the duration difference reverses. These group differences are descriptive and do not by themselves show that microstates improve classification.")
    P.figure("fig5_microstate_maps", f"Group microstate maps vs Koenig 2002 (GEV {gmaps['gev']:.2f}). Polarity aligned for display.")
    P.new_page(1)
    P.figure("fig6_microstate_features", "Microstate features for AD and HC subjects. Each point is one subject.", wide=True)
    P.table("table6_microstate_features", f"AD vs HC microstate features on unsmoothed labels (descriptive). Mean ± SD; p = two-sided Mann-Whitney U, uncorrected for the 12 tests. Longer AD durations hold for these labels; with a {min_seg}-sample ({min_ms:.0f} ms) minimum-segment rule, the mean visit is {ad_sm:.0f} ms in AD vs {hc_sm:.0f} ms in HC, so the direction reverses", [0.55, 0.8, 0.8, 0.55, 0.8, 0.8, 0.55, 0.8, 0.8, 0.55])
    P.columns(2)
    P.h2("Follow-up: Methods")
    P.lead("Question", f"This is a separate study from the EEGNet-hybrid experiment above, and its numbers are not headline results for that experiment. It asks whether a standalone CNN on the A-D microstate label sequence (seq-CNN, the main model here) beats logistic regression on the 24 features computed from the same labels (the primary baseline), and how each changes with training-set size. The preregistered primary comparison is seq-CNN vs logistic regression on balanced accuracy. The EEGNet ensemble is a secondary reference.")
    P.lead("Preregistration and splits", f"The plan was preregistered separately (results/followup_seqcnn/PREREGISTERED.md, see Code Availability) before any prediction from these models existed, and the code was frozen with hashes before launch. It reused the confirmation splits (repeat seeds 3-5, 15 folds) on the same 65 subjects, so it is not independent evidence: logistic regression ({fba(LOG_)}) and the EEGNet ensemble ({fba('eegnet_ens5')}) were already known on these splits, and a one-hot hybrid had been explored on repeat seeds 0-2. With primary labels, logistic regression reproduced the confirmation run's probabilities exactly. Maps were fitted on each fold's training subjects only.")
    P.lead("Labels", f"The primary labels are those of Section III: the best-matching map at every sample, with no smoothing, so these are not conventional smoothed microstate sequences. The secondary version applies the Pycrostates minimum-segment rule {cite('pycro')}: segments shorter than {min_seg} samples ({min_ms:.0f} ms) are merged into their neighbours. Within each comparison, both models use the same labels.")
    P.lead("Models", f"The seq-CNN is the hybrid's microstate branch (Fig. 1) trained alone from scratch, with its own linear head ({seq_params:,} parameters), on one-hot 4 × 512 windows, as a 5-seed ensemble. It used the training settings above without tuning; amplitude jitter and noise act on raw EEG only, so its augmentation is the random crops. Logistic regression used the baseline's fixed settings on features from each whole recording, so the models see the data differently: 4-s windows averaged over the recording vs a whole-recording summary. Secondary rows are the seq-CNN on the 4 |correlation| traces and the EEGNet ensemble, reused from the confirmation run without retraining.")
    P.lead("Tests", f"The primary metric is subject-level balanced accuracy at threshold 0.5. We preregistered {len(fu['tests'])} paired tests, 1 primary and {len(fu['tests']) - 1} secondary, using the same corrected t-test (two-sided, unadjusted).")
    P.lead("Learning curve", "Using primary labels only, we compared the seq-CNN and logistic regression at 20, 35 and 52 training subjects. 52 is the full fold, with one possible subset and so no draws. At 20 and 35 there were 5 draws per size per fold: each class's training subjects were shuffled once per draw and each size took the first n of that order, so the subsets are nested, and the class ratio follows the training fold to the nearest subject. Test subjects did not change. Maps were refitted on each subset only. Both models received the same subset and maps; logistic regression trained on the whole subset, and the seq-CNN held out its early-stopping subjects from inside it (3 of 20, 6 of 35). The curve is descriptive and adds no tests.")
    P.h2("Follow-up: Results")
    P.p(f"Differences below are seq-CNN minus logistic regression, as means over the 15 folds. Seq-CNN balanced accuracy was {fba(SEQ_)} vs {fba(LOG_)} ({fd(1)}, p = {fp(1)}; {ft(1)['better']} better, {ft(1)['tied']} tied and {ft(1)['worse']} worse folds): a small observed lead with substantial uncertainty, not evidence that the CNN is better. Logistic regression was ahead on AUC ({fmean(LOG_, 'auc')} vs {fmean(SEQ_, 'auc')}, {fd(2)}, p = {fp(2)}) and F1 ({fd(3)}, p = {fp(3)}), and the error patterns differed: sensitivity {fmean(SEQ_, 'sensitivity')} and specificity {fmean(SEQ_, 'specificity')} for the CNN, {fmean(LOG_, 'sensitivity')} and {fmean(LOG_, 'specificity')} for logistic regression.")
    P.p(f"With smoothed labels, both models scored lower ({fba('seqcnn_onehot_smoothed')} and {fba('logreg_smoothed')}; seq-CNN minus logistic regression {fd(4)}, p = {fp(4)}), though neither drop was significant ({fd(6)}, p = {fp(6)}; {fd(7)}, p = {fp(7)}). The seq-CNN on |correlation| traces reached {fba('seqcnn_corr')} ({fd(9)} vs logistic regression, p = {fp(9)}). Against the EEGNet ensemble ({fba('eegnet_ens5')}), the differences were {fd(10)} for the seq-CNN (p = {fp(10)}) and {fd(11)} for logistic regression (p = {fp(11)}). None of the {len(fu['tests'])} tests reached p < 0.05, and a non-significant result does not show that the models are equal.")
    bd, ad = (lambda n: fdiff("balanced_accuracy", n)), (lambda n: fdiff("auc", n))
    P.p(f"Table VII and Fig. 7 give the learning curve. On balanced accuracy, the gap narrowed from {bd(20)} at 20 to {bd(52)} at 52, but every difference is within its SD. On AUC, logistic regression stayed ahead at every size ({ad(20)}, {ad(35)}, {ad(52)}), again within the SD. Subsets drawn from one fold overlap, so the SD across draws understates uncertainty about new data. The curve is descriptive, cannot predict performance beyond 52 training subjects, and at most suggests that a larger training cohort could be worth testing.")
    P.columns(1)
    P.table("table7_followup_curve", "Follow-up learning curve, primary labels (descriptive, no tests). Mean ± SD over 15 folds; diff. = seq-CNN minus logistic regression (LR), paired by fold; SD across draws = SD over the 5 draws within a fold, averaged over folds; 52 is the full fold, with one possible subset and so no draws", [0.66, 0.79, 0.79, 0.82, 0.75, 0.79, 0.79, 0.82, 0.75])
    P.columns(2)
    P.figure("fig7_followup_curve", "Follow-up learning curve, primary labels (descriptive, no tests). Top: mean ± SD over 15 folds. Bottom: paired difference, seq-CNN minus logistic regression (LR), mean ± SD over folds.")
    P.h2("Limitations")
    P.bullets(["The confirmation splits are new, but the 65 subjects are the same as in all earlier comparisons, and fusion was chosen after it scored highest on the earlier splits. This is not an independent test set.",
               "The sample is small (13 test subjects per fold), so the study can miss modest real differences. A non-significant result does not show that models are equal.",
               "Training sets overlap across folds. The corrected t-test allows for this but is approximate, and p values are unadjusted for the 9 tests.",
               "Only one dataset, one recording site and eyes-closed rest were used. The group labels come from the dataset authors.",
               "The hybrid is one design. Other ways of adding microstates to a network were not ruled out, although the variants in Table IV gave no significant gain.",
               "The unsmoothed label sequence may partly reflect EEG frequency content (AD shows slower rhythms; see the relative theta and alpha power in Section III) rather than microstate dynamics. This was not tested."])

    P.h1("Conclusion and Future Work")
    P.p(f"We set out to test whether microstate information improves EEGNet for AD vs HC classification under strict subject-wise evaluation. It did not, in the form we tested: the preregistered hybrid ensemble scored {ba(H)} against {ba(E)} for EEGNet (p = {pv(H, E):.2f}). Late fusion of EEGNet and a simple microstate baseline had the highest mean ({ba(F)}), but this was not significantly better than either network ensemble, and needs testing on independent data. The microstate baseline alone reached {ba(L)}, close to the networks at a fraction of the complexity. A separate preregistered follow-up found a small, uncertain balanced-accuracy lead for a standalone microstate-sequence CNN over logistic regression ({fba(SEQ_)} vs {fba(LOG_)}, p = {fp(1)}), with logistic regression ahead on AUC, so the simpler model remains adequate for this dataset.")
    P.p("For the field, the practical implication is about method: subject leakage can make results look much better than they are, and fixing the analysis before testing guards against choosing a lucky variant. These results support further research; they do not support clinical use.")
    P.p("Future work should test the fixed models on an independent cohort and larger datasets such as TDBRAIN and TUH, extend the approach to other conditions such as schizophrenia and depression, and investigate why CPU and MPS runs of EEGNet differed.")

    P.d.add_paragraph("Code Availability and Contributions", style="Heading 5").paragraph_format.keep_with_next = True
    P.p(f"Code, results and the preregistration: [[GitHub URL]]. The follow-up's preregistration and code are in the same repository at results/followup_seqcnn/PREREGISTERED.md, experiments/seqcnn_curve.py and experiments/followup_analysis.py. The confirmation run took {mins / 60:.1f} h on an Apple GPU (MPS) with PyTorch {ver['torch']}, MNE {ver['mne']} and Pycrostates {ver['pycrostates']}. Our contribution is the hybrid model, the experiments and the analysis. EEGNet {cite('lawhern')} and the dataset {cite('data')} are third-party work. NeuroState-Microstates {cite('ns')} is our own previously released open-source tool; it was used for validation only and was not modified. [[Team to confirm against course policy: Claude Code (Anthropic) assisted with code and drafting; the team checked and is responsible for the content.]]").alignment = WD_ALIGN_PARAGRAPH.LEFT  # long repository paths stretch justified lines
    P.d.add_paragraph("References", style="Heading 5").paragraph_format.keep_with_next = True
    unused = set(REFS) - set(order)
    assert not unused, unused
    for k in order:
        P.p(REFS[k], "references").alignment = WD_ALIGN_PARAGRAPH.LEFT
    P.columns(1)  # a section break after the references balances the last two columns
    P.d.core_properties.title = "Do EEG Microstates Improve EEGNet?"
    P.d.core_properties.author = ""
    out = os.path.join(SUB, "NeuroState_paper.docx")
    P.d.save(out)
    print("wrote", out, "refs", len(order))


if __name__ == "__main__":
    main()
