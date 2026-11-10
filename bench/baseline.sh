#!/bin/sh
# Baseline measurements, run one after another (Ollama answers one request at a time).
cd "$(dirname "$0")/.." || exit 1
while pgrep -f "bench/run.py --config plain --split test" >/dev/null; do sleep 30; done
python3 bench/run.py --config plain --split test --sets aime --repeats 4 > results/plain-aime-test.log 2>&1
python3 bench/run.py --config think --split test > results/think-test.log 2>&1
python3 bench/run.py --config think --split test --sets aime --repeats 2 > results/think-aime-test.log 2>&1
echo "baseline done"
