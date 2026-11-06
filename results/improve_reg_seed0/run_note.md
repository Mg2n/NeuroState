# Run note: improve_reg_seed0

`minutes` in `results.json` (220.5) includes about 70 min when the Mac was asleep. The lid was closed on battery at
11:28:21 on 5 Nov 2026 (`pmset -g log`: Clamshell Sleep) and the job was frozen until the lid opened at 12:38:57, so the
real runtime was about 150 min. All of this happened during fold 0. Run on AC from about 12:44 with Low Power Mode on;
3-class seeds 2-4 ran on battery with it off.
