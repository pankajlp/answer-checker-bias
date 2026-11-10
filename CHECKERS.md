# Do answer checkers treat plain and thinking answers differently? (pilot, 2026-11-09)

The question, from [LITERATURE.md](LITERATURE.md): grader mistakes depend on how answers are written, so do they bias a comparison
between two ways of answering (thinking on vs off)?

## What was done
- 1,021 distinct saved answers (all of `results/`, not counting the unchanged copies inside the rescue runs) went through three checkers (`bench/checkers.py`):
  - **ours**: `bench/grader.py`.
  - **Math-Verify 0.9**: Hugging Face's checker, used by lighteval and open-r1.
  - **Hendrycks**: `is_equiv` from the original MATH paper, still used in many harnesses.
- 31 answers had any disagreement. I read every one by hand, and our checker was right in all 31:
  - Hendrycks marked 25 correct answers wrong.
  - Math-Verify marked 4 correct answers wrong (Hendrycks also missed 3 of them).
  - Math-Verify counted 5 unfinished answers as correct.

  Details below.
- Main comparison: the test split, GSM8K + MATH, 300 questions each, one attempt each.

## Result

| | True accuracy | Math-Verify | Hendrycks |
|---|---|---|---|
| plain | 94.7% | 95.0% (missed 0 right, credited 1 wrong) | 92.0% (missed 8 of 284 right, 2.8%) |
| thinking | 99.0% | 98.0% (missed 3 of 297 right) | 95.0% (missed 12 of 297 right, 4.0%) |
| **Measured gain from thinking** | **+4.3 pts** | **+3.0 pts** | **+3.0 pts** |

**Both public checkers understate the true gain by about 30%** (3.0 vs 4.3 points), and for the same reason: they
miss more correct answers when the model thinks. Thinking answers are more carefully typeset, with thin spaces in tuples `(-2,\,1)`,
`\mathbf{v} = \begin{pmatrix}…`, `55°` and `131,250`. Plain answers are terser.

Math-Verify also errs the other way. When a plain answer was cut off before finishing, it sometimes pulled a number out of the
unfinished working (`m + n = 175 + 48 = 223`) and counted it as the answer: 1 on test GSM8K+MATH, 2 on test AIME and 2 on
dev AIME. Plain answers get cut off far more often, so this leniency also favours plain and shrinks the measured gain.

On AIME, where the answers are integers, the checkers barely differ (+20.8 vs +19.2 vs +20.8).

## How much to trust this
- **Direction consistent, size not established.** Math-Verify's split is 3 vs 0 missed answers (a paired test can't separate that from chance at
  this size). Hendrycks' is 12 vs 8. It's a pilot: right mechanism and right direction, but not yet evidence.
- **The reference isn't independent.** Our checker was improved using these same answers. Only the 36 disagreements were read by hand, so
  mistakes all three checkers share would go unnoticed. A paper needs a random sample of agreements checked too, and a second human rater.
- **One model, one comparison.** The claim needs several model families and comparisons where style changes a lot (base vs instruct,
  before/after RL, short vs long reasoning).

## Why it's still promising
In this pilot, checker choice alone moved the measured improvement by 30%. And the bias isn't random noise that averages out: it
consistently works against the method that changes output style. The cheap next step is re-grading published evaluation outputs (no GPU),
where comparisons like RL vs base involve much bigger style changes than here.

## Every disagreement, adjudicated
- **Hendrycks misses (correct answers marked wrong), 25 in total:** `12.00` vs 12, `58500` vs `58,500`, `ellipse` vs `\text{ellipse}`, `[-2, 7]` vs
  `x \in [-2,7]`, `1.75` vs `\frac74`, `C` vs `\text{(C)}`, `4343` vs `4343_6`, `11+11\sqrt5` vs `11\sqrt5+11`, thin-spaced tuples and
  intervals, matrices in another form, `11111111100` vs `11,\!111,…`.
- **Math-Verify misses, 4 in total:** `12^{\mathrm{th}}\text{ grade}` (dev), `131,250` parsed as a list (thinking), `\mathbf{v} = \begin{pmatrix}…` (thinking),
  `55°` (thinking).
- **Math-Verify credited unfinished answers, 5 in total:** plain answers cut off with no final answer, where a number was pulled from the working
  (dev AIME 2025-02 and 2025-26; test AIME 2026-26 and 2026-27; test MATH intermediate_algebra_1510).
- **Our checker wrong:** none of the 31. (It was fixed on these outputs earlier, so this says little about it.)

---

# Scaling up: re-grading MathArena's released HMMT February 2025 outputs

**Data.** [MathArena/hmmt_feb_2025_outputs](https://huggingface.co/datasets/MathArena/hmmt_feb_2025_outputs) (CC BY-NC-SA 4.0): 7,680 full
answers, 64 models × 30 problems × 4 attempts, with MathArena's own verdict for each. HMMT answers are expressions (`2^{25}\cdot 26!`,
`\sqrt{23}-2\sqrt3`, two-root lists), not just integers, so they stress checkers. Script: `bench/matharena_regrade.py`. The data is in
`external/matharena/` and is not redistributed.

**Reference.** MathArena's verdicts. All 26 Math-Verify disagreements were read by hand (`audits/AUDIT.md`): MathArena is right
in 23. The other 3 are decimal approximations of 1−2/π (`0.36338…`), which MathArena rejects; that's grading policy, not an error.
Random samples of 30 Hendrycks rejections, 30 of ours and 40 answers every judge rejects found no MathArena mistakes.

> Numbers below come from `bench/paper_numbers.py` (2026-11-10), which supersedes the first, inline analysis of 2026-11-09.
> Changes: ties now share a rank (GPT-5.2 (high) #2→#11, not #12), and the permutation test uses the documented
> between-model sum of squares. The earlier statistic gave p = 0.031 for Math-Verify without Grok 3 Mini; this one gives 0.002.

## Overall agreement with MathArena

| Checker | Correct answers it marks wrong | Wrong answers it marks right | Rank agreement (Spearman) |
|---|---|---|---|
| Math-Verify | 22 | 4 | 0.999 |
| Hendrycks (original MATH) | 452 | 0 | 0.973 |
| ours (not tuned on this data) | 161 | 0 | 0.989 |

## The key test: does the miss rate depend on *who wrote the answer*?
Among answers MathArena marks correct, each miss is centred on its problem's miss rate (controls for "strong models solve
harder problems with harder answers"); the statistic is the between-model sum of squares; model labels are shuffled within
each problem 10,000 times.

| Checker | p, all models | p, without Grok 3 Mini (low) |
|---|---|---|
| Hendrycks | < 0.001 | < 0.001 |
| Math-Verify | < 0.001 | 0.002 |
| ours | < 0.001 | < 0.001 |

Hendrycks misses 14 points more of GPT OSS 120B (high)'s correct answers than its problems predict, and 8 points fewer of
Gemini 2.5 Pro's. Math-Verify's 22 misses: 10 from Grok 3 Mini (low) (matrix-boxed answers), 8 from the o-series (Unicode `√`), 4 elsewhere.

## What it does to the leaderboard
- **Hendrycks:** 57 of 64 models change rank, 13 by five or more places. GPT-5.2 (xhigh) #1→#8, GPT-5.2 (high) #2→#11,
  Kimi K2 Thinking #9→#20, GLM 4.6 #9→#18, GPT OSS 120B (high) #15→#26, Grok 3 Mini (low) #40→#60.
- **Math-Verify:** 16 models change rank, mostly by one or two places among ties; Grok 3 Mini (low) −8.3 points, #40→#45.

## Reading
1. **The pilot's mechanism holds at scale.** Checker errors aren't random noise: they follow each model's writing style. So they move
   comparisons between models, not just absolute scores.
2. **Math-Verify is good** (26 disagreements in 7,680), but its rare errors still land on particular model families. It's enough to cost
   one model 8 points and to push o4-mini down 2 ranks.
3. **Older string-matching checkers can reorder a leaderboard.** In this data, Hendrycks would demote the top two models to #8 and #11.
4. **What isn't shown yet:** a *published claim* (an improvement reported in a paper) that flips under a different checker. That needs a paper
   whose released outputs compare two training methods. The Sober Look dataset only has scores so far (their full answers are "coming soon").

**Paper:** this analysis is written up in `paper/main.pdf` (LaTeX source in `paper/`).
