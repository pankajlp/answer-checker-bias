# MathArena HMMT February 2025 outputs

Source: [MathArena/hmmt_feb_2025_outputs](https://huggingface.co/datasets/MathArena/hmmt_feb_2025_outputs),
revision `e3fb6c7`, by Balunović et al. (MathArena), licensed CC BY-NC-SA 4.0.

- `hmmt_feb_2025_outputs.parquet` (165 MB) is **not** in this repository; `../fetch_matharena.sh` downloads and checks it.
- `regrade.jsonl` is derived from it by `bench/matharena_regrade.py`: one line per answer with MathArena's
  verdict, our three checkers' verdicts, the extracted answers and the last 300 characters of the answer.
  As a derivative of MathArena's data it is shared under the same licence, CC BY-NC-SA 4.0.
