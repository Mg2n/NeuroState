#!/bin/zsh
# Task 06 step 5 queue, run from experiments/ with the frozen code in this folder.
SNAP=../results/_code_snapshots/step5_2026-11-04
PY=.venv/bin/python
for k in 0 1 2 3 4; do
  o=../results/improve_win8_seed$k; mkdir -p $o
  $PY $SNAP/run_experiment.py --prep ../prepared --out $o --groups A C --repeats 3 --skip-leak --device mps \
      --seed-offset $((1000*k)) --win-sec 8 > $o/log.txt 2>&1
done
for v in onehot corr+feats; do
  n=${v/corr+feats/feats}
  for k in 0 1 2 3 4; do
    o=../results/improve_${n}_seed$k; mkdir -p $o
    $PY $SNAP/run_experiment.py --prep ../prepared --out $o --groups A C --repeats 3 --skip-leak --device mps \
        --seed-offset $((1000*k)) --ms-input $v --models baseline hybrid > $o/log.txt 2>&1
  done
done
