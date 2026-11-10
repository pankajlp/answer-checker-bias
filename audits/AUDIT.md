# Hand audit of the MathArena re-grade (paper, Section 3 and Appendix A)

Single rater (the author), 2026-11-10. `python3 audits/print_samples.py` prints exactly the answers below
(`audits/samples.txt` is its saved output). Full answer texts are in MathArena's dataset (see `external/`).

## Math-Verify vs MathArena: all 26 disagreements

| # | Model | Problem / attempt | Who is right | Why |
|---|---|---|---|---|
| 1 | Kimi K2 Thinking | 29 / 0 | MathArena | box holds an equation chain ending in 14+4√37 |
| 2 | GPT OSS 20B (high) | 11 / 0 | MathArena | answer cut off with no final answer; Math-Verify took 56 from the working |
| 3 | GPT OSS 20B (high) | 17 / 1 | MathArena | 26!·2^25 followed by its 33-digit value (equal) |
| 4 | o3 (high) | 8 / 2 | policy | decimal 0.363380228… for 1−2/π; MathArena rejects approximations |
| 5 | o3-mini (low) | 8 / 3 | policy | decimal 0.36338… for 1−2/π |
| 6 | o4-mini (medium) | 28 / 0 | MathArena | Unicode `√6` |
| 7 | o4-mini (medium) | 28 / 3 | MathArena | Unicode `√6` |
| 8 | o4-mini (medium) | 29 / 2 | MathArena | 2√(197+28√37) = 14+4√37 (both square to 788+112√37) |
| 9 | o4-mini (high) | 25 / 1 | MathArena | Unicode `√23−2√3` |
| 10 | o4-mini (high) | 25 / 2 | MathArena | box holds `XP = \sqrt{23}\;-\;2\sqrt{3}` |
| 11 | o4-mini (high) | 18 / 2 | MathArena | final 2025/101 stated, not boxed (full text read) |
| 12 | o4-mini (low) | 28 / 2 | MathArena | Unicode `√6` |
| 13 | o1 (medium) | 28 / 1 | MathArena | `⎧ MD = √6 ⎫` |
| 14 | GPT-5.1 (high) | 8 / 0 | MathArena | box holds the whole sum `= 1 - \frac{2}{\pi}` |
| 15 | GPT-5-nano (high) | 29 / 0 | MathArena | `boxed{14 + 4\sqrt{37}}` with the backslash missing |
| 16 | Phi-4-reasoning-plus | 8 / 2 | policy | decimal 0.36338022763241885… for 1−2/π |
| 17–26 | Grok 3 Mini (low) | 2 (×3), 7 (×4), 8, 10, 25 | MathArena | answer boxed as a one-column matrix, one token per row |

MathArena right: 23. Grading policy (decimal approximations): 3. MathArena wrong: 0.

## Random samples (seed 2026)
- **30 of 452 answers Hendrycks rejects and MathArena accepts:** all 30 are correct values in another form:
  reordered or separately boxed roots, `\frac{9}{\sqrt{23}}`, `\frac{\sqrt{570}}{12}`, `26!\cdot 2^{25}`,
  labelled (`XP = …`, `MD = …`) or Unicode answers, zero-padded integers (`00029`), one answer with no box.
- **30 of 161 answers our checker rejects and MathArena accepts:** all 30 correct values; mostly `26!\cdot 2^{25}`
  (our checker can't evaluate factorials) and Grok 3 Mini (low) formats.
- **40 answers all four judges reject:** none is correct (spot-checked equivalences, e.g. o3-mini's
  (√(14+2√6)+√(14−2√6))/2 ≈ 3.68 vs 9√23/23 ≈ 1.88). 0/40 gives a 95% upper bound of about 7% on shared misses.
