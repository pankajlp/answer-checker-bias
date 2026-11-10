"""Summarise results, and compare two configurations question by question.

  python3 bench/report.py                       # every config, dev and test
  python3 bench/report.py --split test
  python3 bench/report.py --compare plain think --split dev
  python3 bench/report.py --review plain        # answers the checker was unsure about or got wrong"""
import argparse, json, math, random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / 'results'
SETS = ('gsm8k', 'math', 'aime', 'all')

def load(config, split):
    p = RES / config / f'{split}.jsonl'
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

def vote(rs):
    """One verdict for one attempt-group. With several samples: majority vote over extracted answers."""
    if len(rs) == 1:
        return rs[0]
    votes = Counter(r['extracted'] for r in rs if r['extracted'] is not None)
    top = votes.most_common(1)[0][0] if votes else None
    pick = next((r for r in rs if r['extracted'] == top), rs[0])
    return pick | {'tokens': sum(r['tokens'] or 0 for r in rs), 'seconds': sum(r['seconds'] for r in rs)}

def per_question(rows):
    """One record per question. 'score' is the share of repeats that got it right (0 or 1 without repeats)."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r['id'], r.get('repeat', 0))].append(r)
    by_q = defaultdict(list)
    for (qid, _), rs in groups.items():
        by_q[qid].append(vote(rs))
    out = {}
    for qid, vs in by_q.items():
        n = len(vs)
        out[qid] = vs[0] | {'repeats': n, 'score': sum(v['correct'] for v in vs) / n,
                            'tokens': sum(v['tokens'] or 0 for v in vs) / n, 'seconds': sum(v['seconds'] for v in vs) / n,
                            'truncated': sum(v['truncated'] for v in vs) / n, 'unsure': any(v['unsure'] for v in vs),
                            'answers': [v['extracted'] for v in vs]}
    return out

def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

def summary(config, split):
    qs = per_question(load(config, split))
    if not qs:
        return
    print(f'\n## {config} — {split}')
    print(f"{'set':<10}{'n':>5}{'correct':>9}{'accuracy':>10}   95% CI        tokens/q  sec/q  cut-off  unsure")
    for s in SETS:
        rs = [r for r in qs.values() if s == 'all' or r['set'] == s]
        if not rs:
            continue
        k, n = sum(r['score'] for r in rs), len(rs)
        lo, hi = wilson(k, n) if all(r['repeats'] == 1 for r in rs) else bootstrap([r['score'] for r in rs])
        reps = min(r['repeats'] for r in rs)
        print(f"{s + (f' ×{reps}' if reps > 1 else ''):<10}{n:>5}{k:>9.1f}{100 * k / n:>9.1f}%   {100 * lo:4.1f}–{100 * hi:4.1f}%   "
              f"{sum(r['tokens'] or 0 for r in rs) / n:>8.0f} {sum(r['seconds'] for r in rs) / n:>6.1f} "
              f"{sum(r['truncated'] for r in rs):>8.0f} {sum(r['unsure'] for r in rs):>7}")
    math_rows = [r for r in qs.values() if r['set'] == 'math']
    if math_rows:
        levels = sorted({r['level'] for r in math_rows})
        print('MATH by level: ' + '  '.join(
            f"L{lv} {sum(r['score'] for r in math_rows if r['level'] == lv):g}/{sum(r['level'] == lv for r in math_rows)}"
            for lv in levels))

def bootstrap(scores, n=10000):
    rng = random.Random(0)
    means = sorted(sum(rng.choice(scores) for _ in scores) / len(scores) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]

def paired_p(diffs, n=20000):
    """Two-sided sign-flip permutation test on per-question differences (exact McNemar when scores are 0/1)."""
    d = [x for x in diffs if x != 0]
    if not d:
        return 1.0
    obs = abs(sum(d))
    if len(d) <= 20:
        hits = sum(abs(sum(x if (m >> i) & 1 else -x for i, x in enumerate(d))) >= obs - 1e-12 for m in range(2 ** len(d)))
        return hits / 2 ** len(d)
    rng = random.Random(0)
    hits = sum(abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= obs - 1e-12 for _ in range(n))
    return (hits + 1) / (n + 1)

def compare(a, b, split):
    qa, qb = per_question(load(a, split)), per_question(load(b, split))
    common = sorted(set(qa) & set(qb))
    if not common:
        print('No questions answered by both.')
        return
    print(f'\n## {a} vs {b} — {split}, {len(common)} questions answered by both')
    for s in SETS:
        ids = [i for i in common if s == 'all' or qa[i]['set'] == s]
        if not ids:
            continue
        sa, sb = sum(qa[i]['score'] for i in ids), sum(qb[i]['score'] for i in ids)
        better_a = sum(qa[i]['score'] > qb[i]['score'] for i in ids)
        better_b = sum(qb[i]['score'] > qa[i]['score'] for i in ids)
        p = paired_p([qb[i]['score'] - qa[i]['score'] for i in ids])
        print(f"{s:<6} {a} {100 * sa / len(ids):5.1f}%  {b} {100 * sb / len(ids):5.1f}%  "
              f"diff {100 * (sb - sa) / len(ids):+5.1f} pts | {a} better on {better_a}, {b} better on {better_b}, p = {p:.3f}")
    print('A difference is only worth believing if p is small (say < 0.05) and it holds up on the test split.')

def voting(config, split):
    """Majority voting estimated from independent repeats: for each k, average over every k-subset of a
    question's attempts (ties split evenly), so no attempts are wasted and no subset is cherry-picked."""
    from itertools import combinations
    by = defaultdict(list)
    for r in load(config, split):
        by[(r['set'], r['id'])].append(r)
    for s in sorted({k[0] for k in by}):
        qs = {k: v for k, v in by.items() if k[0] == s}
        n = min(len(v) for v in qs.values())
        if n < 2:
            continue
        print(f'\n## voting with {config} — {split}, {s} ({len(qs)} questions, {n} attempts each)')
        for k in range(1, n + 1):
            total = 0
            for rs in qs.values():
                rs = rs[:n]
                subs = list(combinations(rs, k))
                sc = 0
                for sub in subs:
                    votes = Counter(r['extracted'] for r in sub if r['extracted'] is not None)
                    if not votes:
                        continue
                    top = max(votes.values())
                    winners = [a for a, c in votes.items() if c == top]
                    right = [a for a in winners if any(r['correct'] for r in sub if r['extracted'] == a)]
                    sc += len(right) / len(winners)
                total += sc / len(subs)
            label = 'one attempt' if k == 1 else f'vote of {k}'
            print(f'  {label:<12} {100 * total / len(qs):5.1f}%')

def review(config, split):
    qs = per_question(load(config, split))
    for r in sorted(qs.values(), key=lambda r: r['id']):
        if r['unsure'] or r['score'] < 1:
            tag = 'UNSURE' if r['unsure'] else ('CUT OFF' if r['truncated'] else 'WRONG')
            shown = r['answers'] if r['repeats'] > 1 else r['extracted']
            print(f"{tag:<8} {r['id']}: model {str(shown)[:60]!r}  gold {r['gold'][:60]!r}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--split', choices=['dev', 'test'])
    ap.add_argument('--compare', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--review', metavar='CONFIG')
    ap.add_argument('--voting', metavar='CONFIG', help='majority voting estimated from repeats')
    a = ap.parse_args()
    splits = [a.split] if a.split else ['dev', 'test']
    if a.compare:
        for s in splits:
            compare(*a.compare, s)
    elif a.voting:
        for s in splits:
            voting(a.voting, s)
    elif a.review:
        for s in splits:
            print(f'\n## {a.review} — {s}')
            review(a.review, s)
    else:
        for cfg in sorted(p.name for p in RES.iterdir() if p.is_dir()):
            for s in splits:
                summary(cfg, s)

if __name__ == '__main__':
    main()
