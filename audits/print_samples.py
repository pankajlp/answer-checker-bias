"""Print the random audit samples used in the paper (Appendix A), deterministically.

  python3 audits/print_samples.py

Reads external/matharena/regrade.jsonl. Seed 2026, sample sizes 30 / 30 / 40, in this order."""
import json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
r = [json.loads(l) for l in open(ROOT / 'external/matharena/regrade.jsonl')]
rng = random.Random(2026)

def show(name, xs, k):
    print('=====', name, len(xs))
    for x in rng.sample(xs, min(k, len(xs))):
        print(f"{x['model'][:22]:<22} p{x['problem']:<3} a{x['attempt']} gold={x['gold'][:40]!r:<44} "
              f"MathArena={x['matharena_parsed'][:30]!r:<34} extracted={str(x['extracted'])[:45]!r}")

show('Hendrycks rejects, MathArena accepts', [x for x in r if x['matharena'] and not x['hendrycks']], 30)
show('Ours rejects, MathArena accepts', [x for x in r if x['matharena'] and not x['ours']], 30)
show('All four reject', [x for x in r if not x['matharena'] and not x['ours'] and not x['mathverify'] and not x['hendrycks']], 40)
print('===== Math-Verify vs MathArena: every disagreement')
for x in r:
    if x['mathverify'] != x['matharena']:
        print(f"{x['model']:<22} p{x['problem']:<3} a{x['attempt']} MathArena={x['matharena']} MathVerify={x['mathverify']} "
              f"gold={x['gold']!r} MV_parsed={x['mv_parsed'][:50]!r}")
