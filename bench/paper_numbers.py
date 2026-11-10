"""Compute every number in the paper from saved files, and write them for LaTeX.

  python3 bench/paper_numbers.py

Inputs (no model calls):
  external/matharena/regrade.jsonl   from bench/matharena_regrade.py (MathArena HMMT Feb 2025, 64 models x 30 x 4)
  results/checkers.jsonl             from bench/checkers.py (our Qwen pilot)
Outputs:
  paper/numbers.tex                  \\newcommand macros used in the text
  paper/data/*.dat                   tables for the figures (pgfplots)
The permutation tests use a fixed seed, so reruns give identical output."""
import json, random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'paper'
CHECKERS = {'mathverify': 'Math-Verify', 'hendrycks': 'Hendrycks', 'ours': 'Ours'}
N_PERM = 10000
macros = {}

def mac(name, value):
    macros[name] = value

def fmt(x, d=1):
    return f'{x:.{d}f}'

# ---------------------------------------------------------------- MathArena re-grade
rows = [json.loads(l) for l in open(ROOT / 'external/matharena/regrade.jsonl')]
models = sorted({r['model'] for r in rows})
mac('maAnswers', f'{len(rows):,}'.replace(',', '{,}'))
mac('maModels', len(models))
mac('maProblems', len({r['problem'] for r in rows}))
mac('maCorrect', f"{sum(r['matharena'] for r in rows):,}".replace(',', '{,}'))

for c in CHECKERS:
    fn = sum(r['matharena'] and not r[c] for r in rows)
    fp = sum(r[c] and not r['matharena'] for r in rows)
    mac(f'{c}FN', fn); mac(f'{c}FP', fp)
    mac(f'{c}FNrate', fmt(100 * fn / sum(r['matharena'] for r in rows)))
    print(f'{CHECKERS[c]:<12} misses {fn} correct answers, credits {fp} wrong ones')

def accuracy(rs, key):
    acc = defaultdict(list)
    for r in rs:
        acc[r['model']].append(r[key])
    return {m: 100 * sum(v) / len(v) for m, v in acc.items()}

def ranks(acc):
    """Competition ranking: 1 + number of models strictly better."""
    return {m: 1 + sum(b > a + 1e-9 for b in acc.values()) for m, a in acc.items()}

def spearman(a, b):
    ms = sorted(a)
    def avg_ranks(d):
        order = sorted(ms, key=lambda m: -d[m])
        r, i = {}, 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and abs(d[order[j + 1]] - d[order[i]]) < 1e-9:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = avg_ranks(a), avg_ranks(b)
    n = len(ms)
    ma, mb = sum(ra.values()) / n, sum(rb.values()) / n
    cov = sum((ra[m] - ma) * (rb[m] - mb) for m in ms)
    va = sum((ra[m] - ma) ** 2 for m in ms) ** .5
    vb = sum((rb[m] - mb) ** 2 for m in ms) ** .5
    return cov / (va * vb)

ref = accuracy(rows, 'matharena')
ref_rank = ranks(ref)
shifts = {}
for c in CHECKERS:
    acc = accuracy(rows, c)
    rk = ranks(acc)
    mac(f'{c}Spearman', fmt(spearman(ref, acc), 3))
    big = sorted(models, key=lambda m: -abs(rk[m] - ref_rank[m]))
    shifts[c] = [(m, ref_rank[m], rk[m], acc[m] - ref[m]) for m in big]
    mac(f'{c}MaxDrop', fmt(max(ref[m] - acc[m] for m in models)))
    mac(f'{c}MaxRankShift', max(abs(rk[m] - ref_rank[m]) for m in models))
    mac(f'{c}ModelsMoved', sum(rk[m] != ref_rank[m] for m in models))
    mac(f'{c}ModelsMovedFive', sum(abs(rk[m] - ref_rank[m]) >= 5 for m in models))
    print(f'{CHECKERS[c]:<12} Spearman {spearman(ref, acc):.3f}; largest moves: ' +
          '; '.join(f'{m} #{a}->#{b} ({d:+.1f})' for m, a, b, d in shifts[c][:5]))

# Rank-shift table for the paper: the models Hendrycks moves most, plus their Math-Verify numbers
hen_acc, mv_acc = accuracy(rows, 'hendrycks'), accuracy(rows, 'mathverify')
hen_rank, mv_rank = ranks(hen_acc), ranks(mv_acc)
lines = []
for m, a, b, d in shifts['hendrycks'][:8]:
    lines.append(f"{m.replace('&', '\\&')} & {ref[m]:.1f} & {a} & {hen_acc[m]:.1f} & {b} & {mv_acc[m]:.1f} & {mv_rank[m]} \\\\")
(OUT / 'data').mkdir(parents=True, exist_ok=True)
(OUT / 'data' / 'rankshift_rows.tex').write_text('\n'.join(lines) + '\n')
g = 'GPT-5.2 (high)'
mac('gptRefRank', ref_rank[g]); mac('gptHenRank', hen_rank[g]); mac('gptHenDrop', fmt(ref[g] - hen_acc[g]))
grok = 'Grok 3 Mini (low)'
mac('grokMVDrop', fmt(ref[grok] - mv_acc[grok])); mac('grokRefRank', ref_rank[grok]); mac('grokMVRank', mv_rank[grok])

# ---------------------------------------------------------------- differential error test
def excess_by_model(rs, c):
    """Among answers MathArena marks correct: miss rate per model minus what its problems predict."""
    byp = defaultdict(list)
    for r in rs:
        byp[r['problem']].append(r)
    pmean = {p: sum(not r[c] for r in v) / len(v) for p, v in byp.items()}
    s, n = defaultdict(float), defaultdict(int)
    for r in rs:
        s[r['model']] += (not r[c]) - pmean[r['problem']]
        n[r['model']] += 1
    return {m: s[m] / n[m] for m in s}, n

def perm_test(rs, c, seed=0):
    """Between-model sum of squares of problem-centred misses; model labels shuffled within each problem."""
    byp = defaultdict(list)
    for r in rs:
        byp[r['problem']].append(r)
    groups = []
    for p, v in byp.items():
        miss = [float(not r[c]) for r in v]
        mu = sum(miss) / len(miss)
        groups.append(([r['model'] for r in v], [x - mu for x in miss]))
    count = defaultdict(int)
    for labels, _ in groups:
        for m in labels:
            count[m] += 1
    def stat(assign):
        s = defaultdict(float)
        for labels, res in assign:
            for m, e in zip(labels, res):
                s[m] += e
        return sum(v * v / count[m] for m, v in s.items())
    obs = stat(groups)
    rng = random.Random(seed)
    hits = 0
    for _ in range(N_PERM):
        shuffled = []
        for labels, res in groups:
            res = res[:]
            rng.shuffle(res)
            shuffled.append((labels, res))
        hits += stat(shuffled) >= obs - 1e-12
    return (hits + 1) / (N_PERM + 1)

correct = [r for r in rows if r['matharena']]
for c in ('hendrycks', 'mathverify', 'ours'):
    for tag, rs in (('All', correct), ('NoGrok', [r for r in correct if r['model'] != grok])):
        p = perm_test(rs, c)
        mac(f'{c}Perm{tag}', fmt(p, 3) if p >= 0.001 else '<0.001')
        print(f'{CHECKERS[c]:<12} differential-miss permutation p ({tag}) = {p:.4f}')

# Figure data: excess miss rate per model (percentage points), Hendrycks and Math-Verify
hx, n = excess_by_model(correct, 'hendrycks')
mx, _ = excess_by_model(correct, 'mathverify')
order = sorted(hx, key=lambda m: hx[m])
with open(OUT / 'data' / 'excess.dat', 'w') as f:
    f.write('idx hen mv label\n')
    for i, m in enumerate(order):
        f.write(f"{i} {100 * hx[m]:.2f} {100 * mx[m]:.2f} {{{m}}}\n")
mac('henTopExcessModel', order[-1]); mac('henTopExcess', fmt(100 * hx[order[-1]]))
mac('henLowExcessModel', order[0]); mac('henLowExcess', fmt(-100 * hx[order[0]]))  # shown as 'points fewer'
for m in ('GPT OSS 120B (high)', 'Gemini 2.5 Pro (05-06)'):
    if m in hx:
        print(f'  Hendrycks excess miss rate {m}: {100 * hx[m]:+.1f} pts')
mac('henGptOss', fmt(100 * hx.get('GPT OSS 120B (high)', float('nan'))))

# Model families behind Math-Verify misses
mv_miss = [r for r in correct if not r['mathverify']]
fam = defaultdict(int)
for r in mv_miss:
    fam['grok' if r['model'] == grok else 'oseries' if r['model'].startswith(('o1', 'o3', 'o4')) else 'other'] += 1
mac('mvMissGrok', fam['grok']); mac('mvMissOseries', fam['oseries']); mac('mvMissOther', fam['other'])

# ---------------------------------------------------------------- Qwen pilot (our model, test GSM8K + MATH)
pilot = [json.loads(l) for l in open(ROOT / 'results/checkers.jsonl')]
pilot = [r for r in pilot if r['split'] == 'test' and r['set'] in ('gsm8k', 'math') and r['config'] in ('plain', 'think')]
for cfg in ('plain', 'think'):
    rs = [r for r in pilot if r['config'] == cfg]
    mac(f'pilotN', len(rs))
    for c in CHECKERS:
        acc = 100 * sum(r[c] for r in rs) / len(rs)
        mac(f'pilot{cfg.capitalize()}{c.capitalize()}', fmt(acc))
        mac(f'pilot{cfg.capitalize()}{c.capitalize()}FN', sum(r['ours'] and not r[c] for r in rs))
        mac(f'pilot{cfg.capitalize()}{c.capitalize()}FP', sum(r[c] and not r['ours'] for r in rs))
    mac(f'pilot{cfg.capitalize()}Right', sum(r['ours'] for r in rs))
for c in CHECKERS:
    gain = (sum(r[c] for r in pilot if r['config'] == 'think') - sum(r[c] for r in pilot if r['config'] == 'plain')) / (len(pilot) / 2)
    mac(f'pilotGain{c.capitalize()}', fmt(100 * gain))
    print(f'Pilot: measured gain from thinking with {CHECKERS[c]}: {100 * gain:+.1f} pts')
allp = [r for r in map(json.loads, open(ROOT / 'results/checkers.jsonl')) if not r['config'].endswith('-rescue')]  # rescue runs copy most answers unchanged
mac('pilotAllAnswers', f'{len(allp):,}'.replace(',', '{,}'))
mac('pilotDisagree', sum(len({r['ours'], r['mathverify'], r['hendrycks']}) > 1 for r in allp))

# ---------------------------------------------------------------- write
names = {k: ''.join(ch for ch in k if ch.isalpha()) for k in macros}
with open(OUT / 'numbers.tex', 'w') as f:
    f.write('% Generated by bench/paper_numbers.py. Do not edit by hand.\n')
    for k, v in macros.items():
        f.write(f'\\newcommand{{\\{names[k]}}}{{{v}}}\n')
print(f'wrote {len(macros)} macros to paper/numbers.tex')
