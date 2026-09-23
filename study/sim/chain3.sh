#!/bin/bash
export SUMO_HOME=/usr/local/lib/python3.11/dist-packages/sumo
cd /home/user/TORS/study/sim
python3 campaign.py --jobs ../results/ood_north_jobs.json --out ../results/ood_north.jsonl --workers 4 --label ood8 >> ../results/ood_north.log 2>&1
python3 campaign.py --jobs ../results/boundary_jobs.json --out ../results/boundary.jsonl --workers 4 --label boundary >> ../results/boundary.log 2>&1
echo "FINAL CAMPAIGNS COMPLETE" >> ../results/chain3.log
