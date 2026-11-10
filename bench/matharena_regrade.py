"""Re-grade MathArena's released HMMT Feb 2025 outputs with three checkers and compare with MathArena's verdicts.

  .venv/bin/python bench/matharena_regrade.py

Writes external/matharena/regrade.jsonl (one line per answer, without the long texts)."""
import json, sys
from pathlib import Path
import pyarrow.parquet as pq
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
sys.path.insert(0, str(ROOT / 'bench' / 'third_party'))
from grader import grade, last_boxed
from hendrycks_math_equivalence import is_equiv
from checkers import mathverify

def main():
    t = pq.read_table(ROOT / 'external/matharena/hmmt_feb_2025_outputs.parquet',
                      columns=['problem_idx', 'model_name', 'idx_answer', 'answer', 'gold_answer', 'parsed_answer', 'correct', 'output_tokens'])
    out = []
    for i, r in enumerate(t.to_pylist()):
        text = r['answer'] or ''
        ours, ext, unsure = grade(text, r['gold_answer'], 'math')
        mv, mv_parsed = mathverify(text, r['gold_answer'])
        boxed = last_boxed(text)
        hen = is_equiv(boxed, r['gold_answer']) if boxed is not None else False
        out.append({'problem': r['problem_idx'], 'model': r['model_name'], 'attempt': r['idx_answer'], 'gold': r['gold_answer'],
                    'matharena_parsed': r['parsed_answer'], 'matharena': bool(r['correct']), 'ours': ours, 'ours_unsure': unsure,
                    'extracted': ext, 'mathverify': mv, 'mv_parsed': mv_parsed, 'hendrycks': hen, 'tokens': r['output_tokens'],
                    'tail': text[-300:]})
        if i % 500 == 0:
            print(i, flush=True)
    (ROOT / 'external/matharena/regrade.jsonl').write_text(''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in out))
    for ch in ('ours', 'mathverify', 'hendrycks'):
        agree = sum(o[ch] == o['matharena'] for o in out)
        fn = sum(o['matharena'] and not o[ch] for o in out)
        fp = sum(o[ch] and not o['matharena'] for o in out)
        print(f'{ch:<11} agrees with MathArena on {agree}/{len(out)}; says wrong where MathArena says right: {fn}; says right where MathArena says wrong: {fp}')

if __name__ == '__main__':
    main()
