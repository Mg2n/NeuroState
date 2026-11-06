#!/bin/zsh
# Task 06 step 5 (second queue), run from experiments/ with the frozen code in this folder.
SNAP=../results/_code_snapshots/step5b_2026-11-05
PY=.venv/bin/python
COMMON=(--prep ../prepared --repeats 3 --skip-leak --device mps)
# 3 classes: settings fixed in advance (task 05 defaults), 5 network seeds
for k in 0 1 2 3 4; do
  o=../results/improve_3class_seed$k; mkdir -p $o
  $PY $SNAP/run_experiment.py $COMMON --out $o --groups A F C --seed-offset $((1000*k)) > $o/log.txt 2>&1
done
# regularisation: nested selection once (seed 0), then the same per-fold choices for seeds 1-4
o=../results/improve_reg_seed0; mkdir -p $o
$PY $SNAP/run_experiment.py $COMMON --out $o --groups A C --reg-grid > $o/log.txt 2>&1
for k in 1 2 3 4; do
  o=../results/improve_reg_seed$k; mkdir -p $o
  $PY $SNAP/run_experiment.py $COMMON --out $o --groups A C --seed-offset $((1000*k)) \
      --reg-choices ../results/improve_reg_seed0/reg_choices.csv > $o/log.txt 2>&1
done
