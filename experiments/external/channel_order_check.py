"""Plausibility check of an undocumented channel order using spatial correlation structure.

For a cohort without channel labels, compare its mean 19x19 channel-correlation matrix (1-30 Hz)
with that of ds004504 raw (labelled, Nihon Kohden export order). A hill-climbing search over
permutations finds the best-matching order; agreement with the identity (ds004504 order) is
evidence, not proof, that the columns follow that order.
Usage: python -I channel_order_check.py padic_israel
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import cohorts, verify  # noqa: E402

def mean_corr(recs, n=40):
    Ms = []
    for r in recs[:n]:
        segs, ch, sf, _ = r.load()
        _, raw = verify.fingerprint(segs if isinstance(segs, list) else [segs], ch, sf)
        if raw is None or raw.shape[0] != 19:
            continue
        Ms.append(np.corrcoef(raw))
    return np.nanmean(Ms, 0), len(Ms)

target = sys.argv[1]
ref_recs = [r for r in cohorts.ds004504() if r.recording_id.endswith(":raw")]
R, nr = mean_corr(ref_recs)
T, nt = mean_corr(list(getattr(cohorts, target)()))
iu = np.triu_indices(19, 1)
score = lambda perm: np.corrcoef(R[iu], T[np.ix_(perm, perm)][iu])[0, 1]
ident = list(range(19))
rng = np.random.default_rng(0)
best_overall = None
for start in range(20):
    perm = ident[:] if start == 0 else list(rng.permutation(19))
    s = score(perm); improved = True
    while improved:
        improved = False
        for a in range(19):
            for b in range(a + 1, 19):
                p2 = perm[:]; p2[a], p2[b] = p2[b], p2[a]
                s2 = score(p2)
                if s2 > s + 1e-9:
                    perm, s, improved = p2, s2, True
    if best_overall is None or s > best_overall[0]:
        best_overall = (s, perm)
s, perm = best_overall
names = ref_recs[0].load()[1]
print(f"{target}: n={nt} vs ds004504 n={nr}")
print(f"  similarity with identity order: r={score(ident):.3f}; best permutation found: r={s:.3f}")
print("  positions where best permutation differs from identity:",
      [(names[i], f"col{perm[i]+1}") for i in range(19) if perm[i] != i])
