#!/bin/bash
export SUMO_HOME=/usr/local/lib/python3.11/dist-packages/sumo
cd /home/user/TORS/study/sim
while pgrep -f "campaign.py --jobs ../results/main_jobs.json" > /dev/null; do sleep 30; done
python3 campaign.py --jobs ../results/ood_bypass_jobs.json --out ../results/ood_bypass.jsonl --workers 4 --label ood8 >> ../results/ood_bypass.log 2>&1
python3 campaign.py --jobs ../results/sens_jobs.json --out ../results/sens.jsonl --workers 4 --label sens >> ../results/sens.log 2>&1
echo "CHAIN COMPLETE" >> ../results/chain.log
