#!/bin/zsh
# Phase 4 confirmation: 5 network seeds on new splits (repeat seeds 3-5), Task 05 defaults. Run from experiments/.
# Models and analysis fixed in results/confirmation/PREREGISTERED.md.
SNAP=../results/_code_snapshots/step7_confirmation_2026-11-06
PY=.venv/bin/python
COMMON=(--prep ../prepared --repeats 3 --first-repeat 3 --skip-leak --device mps --groups A C)
for k in 0 1 2 3 4; do
  o=../results/confirmation/seed$k
  [ -e $o ] && { echo "$o exists, stopping"; exit 1; }
  mkdir -p $o
  $PY -W ignore $SNAP/run_experiment.py $COMMON --out $o --seed-offset $((1000*k)) > $o/log.txt 2>&1
done
