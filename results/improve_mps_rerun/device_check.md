# CPU vs MPS device check (task 06, step 1), 2026-11-04

Synthetic tensors (no real data), same initial weights, torch 2.15.0, Apple M4:

| Check | EEGNet | Hybrid |
|---|---|---|
| Time per training epoch, CPU | 45.7 s | 46.7 s |
| Time per training epoch, MPS | 1.8 s | 1.9 s |
| Eval mode: max abs logit difference CPU vs MPS | 5e-8 | 4e-8 |
| Eval mode: max relative gradient difference | 2e-6 | 7e-7 |
| Train mode (BatchNorm batch stats, dropout 0), 20 Adam steps: max abs loss difference | 6e-8 | 1.2e-7 |
| Same, max abs parameter/buffer difference after 20 steps | 2.3e-4 | 2.2e-4 |

Real run: full 5x3 CV of both networks took 20.5 min on MPS vs about 6.7 h on CPU (task 05).
Baseline probabilities are identical in both runs (max difference 0.0), so subjects and folds match.

Data pipeline (random crops, amplitude jitter, noise, shuffling) uses numpy with the same seeds on both
devices; the only known difference is torch's random stream for dropout masks, which is device-specific.

Observation, not explained: the single CPU EEGNet run (fold-mean balanced accuracy 0.852) is above all five
MPS seeds (0.786-0.810, mean 0.795 +/- 0.010) and above the MPS seed mean in 12 of 15 folds. Epochs trained
are similar (CPU 15.5, MPS 13.5-16.2). The hybrid shows no such gap (CPU 0.813, MPS 0.771-0.820).
With one CPU run we cannot tell a lucky dropout stream from a device effect; more CPU EEGNet seeds would.
