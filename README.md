# Answer-checker bias, and a small honest benchmark for a local model

This repository holds two connected pieces of work (November 2026), with every run, log and number needed to check them.

1. **Paper: [*Same Answers, Different Leaderboards: Answer-Checker Errors Depend on Who Wrote the Answer*](paper/main.pdf).**
   Re-grading 7,680 released MathArena answers from 64 models shows that answer-checker errors depend on which model
   wrote the answer (p < 0.001 for all three checkers), enough to drop the #2 model to #11. In our own controlled
   pilot, two public checkers understated the gain from step-by-step thinking by about 30%. Details: [CHECKERS.md](CHECKERS.md).
2. **The benchmark it grew out of** (below): frozen dev/test splits for a local model (qwen3.8:27b through Ollama), a
   careful answer checker, paired statistics, and a test-set ledger. Its main practical result is *rescue*: when the
   model's thinking runs out of tokens, asking it to commit to an answer from its own reasoning adds 10–14 points on AIME,
   confirmed on held-out AIME 2026.

## Reproduce the paper (no GPU, about 30 seconds)
```
python3 bench/paper_numbers.py          # every number, table and figure -> paper/numbers.tex, paper/data/
python3 audits/print_samples.py         # the hand-audited answers (see audits/AUDIT.md)
cd paper && tectonic main.tex           # build the PDF (any LaTeX with fontspec, e.g. xelatex + bibtex)
```
To redo the re-grade from MathArena's raw outputs: `external/fetch_matharena.sh` (pinned revision, checksum),
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `.venv/bin/python bench/matharena_regrade.py`.

## Where the evidence is
| Claim | Evidence |
|---|---|
| Checker verdicts for all 7,680 MathArena answers | `external/matharena/regrade.jsonl` (from `bench/matharena_regrade.py`) |
| Hand audit of disagreements and random samples | `audits/AUDIT.md`, `audits/samples.txt`, `audits/print_samples.py` |
| Pilot: three checkers on all our own answers | `results/checkers.jsonl` (from `bench/checkers.py`) |
| Every model answer we generated, with reasoning where saved | `results/<config>/<split>.jsonl` (one line per answer: question id, answer text, tokens, seconds, verdict, recipe fingerprint) |
| Run logs, as printed while running | `results/*.log` |
| Every look at the test split | `results/TEST_LEDGER.md` (appended automatically by the scripts) |
| Frozen splits | `data/*_dev.jsonl`, `data/*_test.jsonl`, hashes in `data/SPLITS.sha256` |
| Rescue on dev and test | `results/*-rescue/`, `bench/rescue.py`, section *Rescue* below |
| Thinking budget for Qwen Chat | `bench/budget_sim.py`, `results/budget_sim/dev.jsonl`, `results/budget_sim-dev.log` |
| Ollama isn't deterministic (replay failed) | `results/think-replay-test.log`, `bench/replay.py` |
| Literature check | [LITERATURE.md](LITERATURE.md) |

---

# The benchmark

A small, honest benchmark for the local model (qwen3.8:27b through Ollama). It's here to tell
whether a change to how Qwen answers (thinking, voting over several attempts, running Python, a checker,
fine-tuning) really helps, or only looks like it does.

## What's in it
| Set | Source | Dev | Test |
|---|---|---|---|
| GSM8K | grade-school word problems (OpenAI, test split) | 60 | 150 |
| MATH-500 | competition maths, levels 1–5 (HuggingFaceH4/MATH-500) | 60 | 150 |
| AIME | hard competition maths, integer answers (MathArena) | 30 (2025) | 30 (2026) |

GSM8K and MATH-500 are nearly saturated (plain Qwen scored 98% on dev), so they mostly guard against
regressions. AIME is where improvements can show. It's small, so run it with `--repeats 4`: each problem is
answered 4 times with different seeds and the score is the average, which cuts the luck.

The splits are drawn once with a fixed seed and frozen: `data/SPLITS.sha256` holds their hashes, and
`bench/make_splits.py` refuses to change them.

## Rules (the reason this exists)
1. **Tune on dev, measure on test.** Try ideas, prompts and settings on `--split dev` as often as you like.
   Run `--split test` only once a recipe is final. Every test run is logged in `results/TEST_LEDGER.md`,
   so it's visible how often the test set was looked at.
2. **Recipes are fixed.** A configuration in `bench/run.py` (`CONFIGS`) can't be edited after it has
   results: the runner refuses. Add a new name instead.
3. **Compare question by question.** `report.py --compare A B` uses a paired sign-flip permutation test
   (the exact McNemar test when there are no repeats). With 150 questions per set, differences of a few
   points are usually noise; on 30 AIME problems even 10 points can be.
4. **Public benchmarks may be in the model's training data.** Treat them as a sanity check; your own tasks
   are the more trustworthy measure.

## Commands
```
python3 bench/run.py --config plain                 # dev split
python3 bench/run.py --config plain --split test    # final measurement
python3 bench/run.py --config plain --sets aime --repeats 4   # AIME, averaged over 4 runs
bench/baseline.sh                                   # the baseline runs, one after another
python3 bench/report.py                             # all results
python3 bench/report.py --compare plain think --split dev
python3 bench/report.py --review plain              # wrong / unsure answers, to check the checker
python3 bench/regrade.py                            # re-check saved answers after a checker fix
python3 -m unittest tests/test_grader.py            # answer-checker tests
```
Runs can be stopped (Ctrl-C) and resumed; finished answers are kept. While a run is going, Ollama is
busy, so Qwen Chat replies will wait their turn.

## Configurations
- `plain`: thinking off, one attempt (how Qwen Chat answers by default).
- `think`: thinking on, one attempt, up to 32,000 tokens.
- `think-b`: identical recipe to `think`, re-run on test AIME because the first run didn't save reasoning.
- `<config>-rescue`: made by `bench/rescue.py` from a finished run (cut-off answers rescued, the rest copied).

Both use the model's own sampling settings (temperature 1), with a fixed seed per question so reruns
repeat as closely as Ollama allows.

## Baseline (test split, 2026-11-09)
| | GSM8K | MATH-500 | AIME 2026 | time per question |
|---|---|---|---|---|
| `plain` (thinking off) | 96.7% | 92.7% | 49.2% (×4) | 20 s |
| `think` (thinking on) | 98.7% | 99.3% | 70.0% (×2) | 46 s (AIME: 5.7 min) |

Thinking is a real gain on MATH (p = 0.006) and AIME (p = 0.014); GSM8K's difference is noise.
Most remaining AIME misses with thinking are answers cut off at 32,000 tokens (8 of 60), not wrong answers.

## Rescue: confirmed on the test split (2026-11-10)
Rescue (`bench/rescue.py`): when an answer runs out of tokens with no final answer, show the model the end of its own
reasoning and ask it to commit (thinking off, 2,000 tokens). The recipe was fixed on dev (AIME 2025) and not changed on test.

| AIME | dev 2025 (×4) | test 2026 | test, vote of all attempts |
|---|---|---|---|
| plain → plain-rescue | 42.5 → 56.7 (+14.2, p = 0.004) | 49.2 → 63.3 (+14.2, 12–0, p < 0.001), ×4 | 60.0 → 80.0 (vote of 4) |
| think → think-rescue | 68.3 → 78.3 (+10.0, 8–0, p = 0.008) | 76.7 → 86.7 (+10.0, 5–0, p = 0.062), ×2 (`think-b`) | 81.7 → 90.0 (vote of 2) |

- Same gains on dev and test. Thinking's test p alone is 0.06 because only 5 problems differ (0.0625 is the smallest p possible
  with 5); counting dev and test together, rescue is better on 13 problems and worse on 0 (p = 0.0002).
- Rescue adds about 8 seconds per attempt on average. 5 of 13 rescued thinking answers still gave no boxed answer.
- `think-b` is the same recipe as `think`, re-run because the first test run didn't save reasoning. Ollama isn't
  deterministic here (same seed gave different reasoning), so the two runs differ by chance: 70.0 vs 76.7 (p = 0.34).

## Answer-key fixes
`data/answer_key_fixes.json` lists official answers that are wrong, with the working. The frozen data is
never edited; the runner and `regrade.py` use the fixed answer.

## Files
- `bench/grader.py`: pulls the final `\boxed{}` answer and checks it against the gold answer. It handles
  fractions, roots, π, units, degrees, tuples, intervals, matrices, answer lists and algebraic expressions
  (the expression is checked by plugging in numbers). Anything it can't decide is marked *unsure*.
- `bench/run.py`: runs a configuration and saves every answer to `results/<config>/<split>.jsonl`.
- `bench/report.py`: accuracy with 95% intervals, results by MATH level, paired comparisons, voting.
- `bench/rescue.py`, `bench/replay.py`, `bench/budget_sim.py`: rescue, the failed exact-replay attempt, and the
  thinking-budget simulation behind Qwen Chat's 16,000-token budget (dev: 55.0% → 73.3% with rescue, 4.2 min average).
- `bench/checkers.py`, `bench/matharena_regrade.py`, `bench/paper_numbers.py`: the checker study and the paper's numbers.

## Licence
Code: MIT. Our model outputs and logs: CC BY 4.0. `external/matharena/regrade.jsonl` is derived from MathArena's
data and is CC BY-NC-SA 4.0. Benchmark questions belong to their sources (GSM8K and MATH: MIT; AIME problems: MAA,
taken from MathArena's datasets).
