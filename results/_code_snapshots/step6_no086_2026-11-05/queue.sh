#!/bin/zsh
# 3 classes with sub-086 fully excluded (same outer folds, seeds and settings as improve_3class). Run from experiments/.
SNAP=../results/_code_snapshots/step6_no086_2026-11-05
PY=.venv/bin/python
COMMON=(--prep ../prepared --repeats 3 --skip-leak --device mps --groups A F C --exclude sub-086)
for k in 0 1 2 3 4; do
  o=../results/improve_3class_no086_seed$k; mkdir -p $o
  $PY $SNAP/run_experiment.py $COMMON --out $o --seed-offset $((1000*k)) > $o/log.txt 2>&1
done
