"""Re-create the reasoning of saved answers that ran out of room, for runs made before reasoning was stored.

  python3 bench/replay.py --base think --split test

Only answers that hit the token limit with no final answer are re-run (they are the only ones rescue needs),
with the exact same recipe and seed. A replay counts only if it reproduces the original exactly: same token
count, same reasoning length, same visible answer. The first mismatch stops the script, because then the
model isn't deterministic and replaying just some answers would bias the comparison (rerun everything instead).
Writes results/<base>-replay/<split>.jsonl: every original row, with the reasoning filled in where replayed."""
import argparse, datetime, json, sys, time, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
from run import CONFIGS, fingerprint, ask

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, choices=CONFIGS)
    ap.add_argument('--split', default='test', choices=['dev', 'test'])
    a = ap.parse_args()
    cfg = CONFIGS[a.base]
    rows = [json.loads(l) for l in (ROOT / 'results' / a.base / f'{a.split}.jsonl').read_text().splitlines()]
    if any(r['fingerprint'] != fingerprint(cfg) for r in rows):
        sys.exit('recipe changed since the original run; cannot replay')
    out = ROOT / 'results' / f'{a.base}-replay' / f'{a.split}.jsonl'
    out.parent.mkdir(parents=True, exist_ok=True)
    key = lambda r: (r['id'], r['sample'], r.get('repeat', 0))
    done = {key(r): r for r in map(json.loads, out.read_text().splitlines())} if out.exists() else {}
    questions = {}
    for f in (ROOT / 'data').glob(f'*_{a.split}.jsonl'):
        for q in map(json.loads, f.read_text().splitlines()):
            questions[q['id']] = q
    need = [r for r in rows if r['truncated'] and r['extracted'] is None and not r.get('thinking') and key(r) not in done]
    if a.split == 'test' and need:
        with open(ROOT / 'results' / 'TEST_LEDGER.md', 'a') as f:
            f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} test run: exact replay of `{a.base}` cut-off answers "
                    f"to recover reasoning, {len(need)} answers (verdicts unchanged)\n")
    print(f'{len(need)} answers to replay', flush=True)
    with open(out, 'a') as f:
        for r in rows:
            k = key(r)
            if k in done:
                continue
            if r in need:
                rp = r.get('repeat', 0)
                seed = zlib.crc32(f"{r['id']}-{r['sample']}".encode() + (f'-r{rp}'.encode() if rp else b''))
                t0 = time.time()
                res = ask(cfg, questions[r['id']]['question'], seed)
                msg = res.get('message', {})
                thinking, content = msg.get('thinking') or '', msg.get('content', '')
                same = (res.get('eval_count') == r['tokens'] and len(thinking) == r['thinking_chars']
                        and content == r['content'] and res.get('done_reason') == 'length')
                print(f"  {r['id']} r{rp}: {'reproduced' if same else 'MISMATCH'} "
                      f"(tokens {res.get('eval_count')} vs {r['tokens']}, reasoning {len(thinking)} vs {r['thinking_chars']} chars) "
                      f"{time.time() - t0:.0f}s", flush=True)
                if not same:
                    sys.exit('Not deterministic: replaying only some answers would bias the comparison. Rerun the whole config instead.')
                r = dict(r, thinking=thinking, replayed=True)
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            f.flush()
    print('replay done', flush=True)

if __name__ == '__main__':
    main()
