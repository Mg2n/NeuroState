#!/bin/zsh
# Task 09: seq-CNN follow-up, fixed in results/followup_seqcnn/PREREGISTERED.md. Run from experiments/.
# Launch only after the user types "go":
#   nohup caffeinate -ims /bin/zsh ../results/followup_seqcnn/_code_snapshot/queue.sh > ../results/followup_seqcnn/_code_snapshot/queue.log 2>&1 &
SNAP=../results/followup_seqcnn/_code_snapshot
R=../results/followup_seqcnn
PY=.venv/bin/python
COMMON=(--prep ../prepared --repeats 3 --first-repeat 3 --skip-leak --device mps --groups A C)
run() {
  o=$R/$1; shift
  [ -e $o ] && { echo "$o exists, stopping"; exit 1; }
  mkdir -p $o
  $PY -W ignore $SNAP/run_experiment.py $COMMON "$@" --out $o > $o/log.txt 2>&1 || { echo "$o failed, stopping"; exit 1; }
}
for k in 0 1 2 3 4; do
  run main_seed$k   --models baseline seqcnn --ms-input onehot --seed-offset $((1000*k))                 # primary labels
done
for k in 0 1 2 3 4; do
  run smooth_seed$k --models baseline seqcnn --ms-input onehot --min-segment 4 --seed-offset $((1000*k)) # secondary labels
done
for k in 0 1 2 3 4; do
  run corr_seed$k   --models seqcnn --ms-input corr --seed-offset $((1000*k))                            # secondary input
done
o=$R/curve
[ -e $o ] && { echo "$o exists, stopping"; exit 1; }
mkdir -p $o
$PY -W ignore $SNAP/seqcnn_curve.py --prep ../prepared --out $o --sizes 20 35 --draws 5 --seed-offsets 0 1000 2000 3000 4000 \
  --first-repeat 3 --repeats 3 --device mps > $o/log.txt 2>&1 || { echo "$o failed, stopping"; exit 1; }
# Analysis, after checking the runs (from experiments/):
#   .venv/bin/python -W ignore $SNAP/followup_analysis.py --main-runs $R/main_seed{0..4} --smooth-runs $R/smooth_seed{0..4} \
#     --corr-runs $R/corr_seed{0..4} --curve-run $R/curve --confirmation ../results/confirmation --out $R
