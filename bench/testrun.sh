#!/bin/sh
# Test-set confirmation of rescue (recipe fixed on dev; nothing is tuned here).
cd "$(dirname "$0")/.." || exit 1
# plain rescue on test: done 2026-11-10
# replay failed (model not deterministic); full re-run instead:
python3 bench/run.py --config think-b --split test --sets aime --repeats 2 > results/think-b-aime-test.log 2>&1
python3 bench/rescue.py --base think-b --split test > results/think-b-rescue-test.log 2>&1
echo "test runs done"
