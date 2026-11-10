#!/bin/sh
# Dev experiments for voting and rescue on AIME 2025 (dev only).
cd "$(dirname "$0")/.." || exit 1
python3 bench/run.py --config plain --sets aime --repeats 4 > results/plain-aime-dev.log 2>&1
python3 bench/rescue.py --base plain --split dev > results/plain-rescue-dev.log 2>&1
python3 bench/run.py --config think --sets aime --repeats 4 > results/think-aime-dev.log 2>&1
python3 bench/rescue.py --base think --split dev > results/think-rescue-dev.log 2>&1
echo "dev runs done"
