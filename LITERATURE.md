# Literature check: "How much of a reported reasoning gain survives careful measurement?"

Checked 2026-11-09 using web searches and abstract pages. Summaries of papers not read in full are marked "(abstract)". Re-read anything before citing it.

## The four pieces of the idea, and who has done them

| Piece | Already covered? | Closest work |
|---|---|---|
| Seed and run-to-run noise on small sets (AIME) | **Yes, thoroughly** | Hochlehnert et al. 2025, *A Sober Look at Progress in LM Reasoning* (arXiv 2504.07086). Single-seed AIME results are unstable (1 question is more than 3 points); recommends about 10 seeds. Under a standard setup, many claimed RL gains shrink to modest or non-significant. |
| Answer-key errors | **Yes** | Vendrow et al. 2025, *Do LLM Benchmarks Test Reliability?* (arXiv 2502.03461). About 5% of GSM8K is flawed; "platinum" cleaned versions of 15 benchmarks. Our GSM8K-1309 error is probably already in their list. |
| Token budget and truncation | **Yes, recently** | de Souza & Panisson 2026, *Who Thinks Best Depends on How Long You Let Them* (arXiv 2608.12150, abstract). Model rankings reverse across budgets of 64–4,096 tokens on all three benchmarks. No forced-answer or rescue step is mentioned in the abstract. |
| Answer-checker (grader) errors | **Partly** | Huang et al., *From Accuracy to Robustness: A Study of Rule- and Model-based Verifiers in Mathematical Reasoning* (arXiv 2505.22203; earlier titled *Pitfalls of…*; abstract). Rule-based checkers produce substantial false negatives on format variations; model-based judges can be fooled. Focus is on RL training rewards, not on evaluation claims. |
| Grader choice changes a comparison | **Partly, one paper** | Munjal et al. 2026 (arXiv 2601.13244), Sec. 4.4. Qwen3-14B base vs instruct gap: 10.8 points with a regex grader, 0.8 with Math-Verify. Kimi-K2's direction flips. This is a side analysis: no counts of which outputs the grader got wrong, by model. |
| Breaking down variance (items, seeds, prompts, judges) | **Yes, as a framework** | *Hidden Measurement Error in LLM Pipelines* (arXiv 2604.11581) applies generalizability theory. In their setup, items are 43% of variance, item×system 21%, sampling 20%, prompt under 1%. |
| Checker failures by answer form | **Yes (2026)** | Xin 2026, *Where the Verifier Fails* (arXiv 2609.01354, abstract). Constructed equivalent answers; most failures are whitespace/punctuation; implementations differ by 41 points. By answer form, not by model; no leaderboard effects. Added 2026-11-10. |
| MathArena's own grading | **Describes it** | Dekoninck et al. 2026 (arXiv 2605.00674): parser asks models to restate unparseable answers; LLM judge and manual review of disagreements. Added 2026-11-10. |

## What looks open

1. **Differential grader error (the strongest gap).** Grader mistakes aren't random: they depend on output style. Here, both runs had checker errors, but of different kinds. Plain answers tripped it with "137\frac12", "12th grade" and a missing base subscript. Thinking answers tripped it with matrices written as equations, `\\[6pt]` row spacing and `\pi^{2}`. The counts are tiny (3 per run), but the kind of error followed the output style. So grader error can **inflate or hide the very improvement being claimed** when a method changes how answers are written (thinking vs not, RL vs base, voting). In epidemiology this is *differential misclassification*, a well-understood bias. Munjal et al. show it can matter, but nobody seems to have measured it directly: human-adjudicated grader error rates **per condition**, and how much of a claimed gain they explain.
2. **An "error budget" for one claimed gain.** Each source of error is studied on its own. No paper takes the same saved outputs and reports how many points of the gain come from the grader, key errors, seeds and the token budget, all together.
3. **Re-grading published claims.** Many reasoning papers release their evaluation outputs. Re-grading them with several checkers plus human adjudication would test whether published gains survive. This is the same kind of work as your replication projects, and it needs no GPU.
4. **Rescue vs scoring truncation as wrong.** The budget paper scores cut-off answers as wrong. Whether a cheap "commit to an answer" step changes rankings is a small, testable add-on, but it's close to s1-style budget forcing (Muennighoff et al. 2025), so it's not a headline on its own.

## Honest assessment
- No single piece is new. A paper would need to be framed around **(1) differential grader error**, with (2) and (3) as the evidence.
- Realistic venue: an arXiv preprint and an evaluation or reproducibility workshop. A main conference would need several model families, several public checkers (Math-Verify, the lm-eval-harness and LightEval extractors, an LLM judge) and re-grading of at least a few published papers' released outputs.
- Next cheap step (no new model runs): run Math-Verify and one or two other public checkers on the answers already saved in `results/`, adjudicate the disagreements by hand, and see whether checker error differs between `plain` and `think`. If it clearly does, the idea has legs.

## Sources
- https://arxiv.org/abs/2504.07086 (A Sober Look at Progress in LM Reasoning)
- https://arxiv.org/abs/2502.03461 (Do LLM Benchmarks Test Reliability?)
- https://arxiv.org/abs/2608.12150 (Who Thinks Best Depends on How Long You Let Them)
- https://arxiv.org/abs/2505.22203 (Pitfalls of Rule- and Model-based Verifiers)
- https://arxiv.org/html/2601.13244 (Do Instruction-Tuned Models Always Perform Better Than Base Models?)
- https://arxiv.org/html/2604.11581v3 (Hidden Measurement Error in LLM Pipelines)
- https://arxiv.org/pdf/2505.14625 (TinyV: false negatives in verification)
- https://github.com/ZubinGou/math-evaluation-harness (cross-framework math variance above 5%, README claim)
