"""Run three answer checkers on every saved answer and record where they disagree.

  .venv/bin/python bench/checkers.py

Checkers:
  ours       bench/grader.py (the verdict already saved in results/)
  mathverify Hugging Face Math-Verify 0.9 (as used by lighteval / open-r1): parse(full answer) vs parse($gold$)
  hendrycks  the original MATH paper's is_equiv string normaliser, on the last \\boxed{} answer
Output: results/checkers.jsonl (one line per answer)."""
import glob, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
sys.path.insert(0, str(ROOT / 'bench' / 'third_party'))
from grader import last_boxed, extract
from hendrycks_math_equivalence import is_equiv
from math_verify import parse, verify

def mathverify(content, gold):
    try:
        g = parse(f'${gold}$')
        p = parse(content)
        return bool(verify(g, p)), str(p[1] if len(p) > 1 else (p[0] if p else None))
    except Exception as e:
        return False, f'error: {e}'

def main():
    out = []
    for path in sorted(glob.glob(str(ROOT / 'results' / '*' / '*.jsonl'))):
        cfg, split = Path(path).parent.name, Path(path).stem
        for r in map(json.loads, open(path)):
            mv, mv_parsed = mathverify(r['content'], r['gold'])
            boxed = last_boxed(r['content'])
            if boxed is None and r['set'] == 'gsm8k':
                boxed = extract(r['content'], 'gsm8k')[0]
            hen = is_equiv(boxed, r['gold']) if boxed is not None else False
            out.append({'config': cfg, 'split': split, 'id': r['id'], 'set': r['set'], 'repeat': r.get('repeat', 0),
                        'gold': r['gold'], 'extracted': r['extracted'], 'truncated': r['truncated'],
                        'ours': r['correct'], 'mathverify': mv, 'mv_parsed': mv_parsed, 'hendrycks': hen})
    (ROOT / 'results' / 'checkers.jsonl').write_text(''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in out))
    dis = [o for o in out if len({o['ours'], o['mathverify'], o['hendrycks']}) > 1]
    print(f'{len(out)} answers checked, {len(dis)} with any disagreement')
    for o in dis:
        print(f"{o['config']:<13}{o['split']:<5}{o['id']:<42} ours={int(o['ours'])} mv={int(o['mathverify'])} hen={int(o['hendrycks'])} "
              f"| ext {str(o['extracted'])[:45]!r} | mv {o['mv_parsed'][:30]!r} | gold {o['gold'][:40]!r}")

if __name__ == '__main__':
    main()
