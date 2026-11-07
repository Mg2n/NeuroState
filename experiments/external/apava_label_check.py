"""Check APAVA labels and file order against Smith et al. 2017 (Edinburgh DataShare 10.7488/ds/2109).

SpainADdata.mat holds per-subject 16x16 PLI matrices (alpha, beta) and patient1_control0.
We recompute alpha PLI from each preproctrialsNN.mat and match it to the published matrices.
"""
import sys, os
import numpy as np, scipy.io as sio
from scipy.signal import butter, filtfilt, hilbert
sys.path.insert(0, os.path.dirname(__file__))
import cohorts

pub = sio.loadmat(os.path.join(cohorts.EXT, "apava_spain", "metadata", "SpainADdata.mat"))
lab = pub["patient1_control0"].ravel().astype(int)
print("label vector length:", len(lab), "AD:", int(lab.sum()), "controls:", int((lab == 0).sum()))

def pli(trials, fs, band):
    b, a = butter(4, [band[0] / (fs / 2), band[1] / (fs / 2)], btype="band")
    M = 0
    for x in trials:
        ph = np.angle(hilbert(filtfilt(b, a, x, axis=1), axis=1))
        d = ph[:, None, :] - ph[None, :, :]
        M = M + np.abs(np.mean(np.sign(np.sin(d)), axis=2))
    return M / len(trials)

recs = list(cohorts.apava_spain())
iu = np.triu_indices(16, 1)
C = np.zeros((23, 23))
for k, r in enumerate(recs):
    tr, ch, fs, _ = r.load()
    m = pli(tr, fs, (8, 13))
    for j in range(23):
        C[k, j] = np.corrcoef(m[iu], pub["SpainADdataPLIalpha"][:, :, j][iu])[0, 1]
best = C.argmax(1)
print("file -> best published index (1-based), r, runner-up r")
ok = True
for k in range(23):
    s = np.sort(C[k])[::-1]
    print(f"  preproctrials{k+1:02d} -> {best[k]+1:2d}  r={s[0]:.3f}  next={s[1]:.3f}")
    ok &= best[k] == k
print("identity mapping:", bool(ok))

# Robustness: several band definitions, alpha+beta combined, optimal one-to-one assignment.
from scipy.optimize import linear_sum_assignment
res = {}
trials_all = [r.load() for r in recs]
for name, ba, bb in [("8-13/13-30", (8, 13), (13, 30)), ("8-12/12-30", (8, 12), (12, 30)), ("7.5-12.5/12.5-30", (7.5, 12.5), (12.5, 30))]:
    S = np.zeros((23, 23))
    for k, (tr, ch, fs, _) in enumerate(trials_all):
        ma, mb = pli(tr, fs, ba), pli(tr, fs, bb)
        for j in range(23):
            S[k, j] = (np.corrcoef(ma[iu], pub["SpainADdataPLIalpha"][:, :, j][iu])[0, 1]
                       + np.corrcoef(mb[iu], pub["SpainADdataPLIbeta"][:, :, j][iu])[0, 1])
    rows, cols = linear_sum_assignment(-S)
    ranks = [int((S[k] > S[k, k]).sum()) + 1 for k in range(23)]
    res[name] = (int((cols == rows).sum()), ranks)
    print(f"{name}: assignment==identity for {int((cols == rows).sum())}/23; rank of own index per file: {ranks}")
