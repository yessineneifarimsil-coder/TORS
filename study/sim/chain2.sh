#!/bin/bash
# After the main campaign: produce results.json, plan the boundary-localisation
# runs from it, and execute them once the other campaigns have finished.
export SUMO_HOME=/usr/local/lib/python3.11/dist-packages/sumo
cd /home/user/TORS/study
until [ "$(wc -l < results/main.jsonl)" -ge 12960 ]; do sleep 60; done
echo "main complete, building results.json" >> results/chain2.log
nice -n 19 python3 analysis/run_analysis.py >> results/chain2.log 2>&1
nice -n 19 python3 analysis/boundary.py plan >> results/chain2.log 2>&1
# wait for the ood_bypass + sens chain to clear before taking the cores
while pgrep -f "campaign.py --jobs ../results/\(ood_bypass\|sens\)_jobs.json" > /dev/null; do sleep 30; done
until [ -f results/chain.log ]; do sleep 30; done
cd sim
python3 campaign.py --jobs ../results/boundary_jobs.json --out ../results/boundary.jsonl --workers 4 --label boundary >> ../results/boundary.log 2>&1
echo "BOUNDARY COMPLETE" >> ../results/chain2.log
