"""Re-check every saved answer with the current checker and answer-key fixes (run after changing either).
The model is not called; only the verdicts in results/*/*.jsonl change, and changes are printed."""
import glob, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
from grader import grade
from run import gold_for

for p in sorted(glob.glob(str(ROOT / 'results' / '*' / '*.jsonl'))):
    rows = [json.loads(l) for l in open(p)]
    for r in rows:
        gold = gold_for(r['id'], r['gold'])
        ok, ex, un = grade(r['content'], gold, r['set'])
        if (ok, un, gold) != (r['correct'], r['unsure'], r['gold']):
            print(f"{Path(p).parent.name}/{Path(p).name} {r['id']}: {r['correct']} -> {ok}")
        r.update(gold=gold, correct=ok, extracted=ex, unsure=un)
    Path(p).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
