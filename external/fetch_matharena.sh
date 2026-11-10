#!/bin/sh
# Download MathArena's HMMT February 2025 outputs at the exact revision used in the paper, and check it.
# Licence: CC BY-NC-SA 4.0 (MathArena). Only needed to re-run bench/matharena_regrade.py;
# paper numbers can be regenerated from external/matharena/regrade.jsonl without it.
set -e
cd "$(dirname "$0")/matharena"
REV=e3fb6c74f24eabf83413eb9e62b9816c1f3f7d2e
curl -L -o hmmt_feb_2025_outputs.parquet \
  "https://huggingface.co/datasets/MathArena/hmmt_feb_2025_outputs/resolve/$REV/data/train-00000-of-00001.parquet"
echo "afb629b9ff576f74426acab054b2036244ba539ebaacfd118bb923163619822a  hmmt_feb_2025_outputs.parquet" | shasum -a 256 -c
