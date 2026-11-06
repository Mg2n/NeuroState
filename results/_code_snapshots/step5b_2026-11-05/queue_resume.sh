#!/bin/zsh
# Resume of queue.sh: 3-class seeds 2-4, then regularisation. Run from experiments/.
SNAP=../results/_code_snapshots/step5b_2026-11-05
PY=.venv/bin/python
COMMON=(--prep ../prepared --repeats 3 --skip-leak --device mps)
for k in 2 3 4; do
  o=../results/improve_3class_seed$k; mkdir -p $o
  $PY $SNAP/run_experiment.py $COMMON --out $o --groups A F C --seed-offset $((1000*k)) > $o/log.txt 2>&1
done
o=../results/improve_reg_seed0; mkdir -p $o
$PY $SNAP/run_experiment.py $COMMON --out $o --groups A C --reg-grid > $o/log.txt 2>&1
for k in 1 2 3 4; do
  o=../results/improve_reg_seed$k; mkdir -p $o
  $PY $SNAP/run_experiment.py $COMMON --out $o --groups A C --seed-offset $((1000*k)) \
      --reg-choices ../results/improve_reg_seed0/reg_choices.csv > $o/log.txt 2>&1
done
