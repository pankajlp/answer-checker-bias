"""Run a model configuration over a frozen split and record every answer.

  python3 bench/run.py --config plain                  # dev split (default): use this while tuning
  python3 bench/run.py --config plain --split test     # test split: only to measure, never to tune

Results go to results/<config>/<split>.jsonl, one line per answer, written as they finish, so a run
can be stopped and resumed. Every test-split run is logged in results/TEST_LEDGER.md."""
import argparse, datetime, hashlib, json, sys, time, urllib.request, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
from grader import grade

OLLAMA = 'http://localhost:11434/api/chat'
PROMPT = '{question}\n\nPlease reason step by step, and put your final answer within \\boxed{{}}.'

# Each configuration is a fixed recipe. Add new ones (self-consistency, tools...) instead of editing old ones.
CONFIGS = {
    'plain': {'model': 'qwen3.8:27b', 'think': False, 'samples': 1, 'num_predict': 6000},
    'think': {'model': 'qwen3.8:27b', 'think': True, 'samples': 1, 'num_predict': 32000, 'num_ctx': 40960},
    # Same recipe as 'think', re-run because the first test run predates saving reasoning (needed by rescue.py),
    # and Ollama isn't deterministic on this machine, so the cut-off answers couldn't be replayed exactly.
    'think-b': {'model': 'qwen3.8:27b', 'think': True, 'samples': 1, 'num_predict': 32000, 'num_ctx': 40960},
}

FIXES = json.loads((ROOT / 'data' / 'answer_key_fixes.json').read_text())

def gold_for(qid, gold):
    """Official answer, unless data/answer_key_fixes.json documents an error in the key."""
    fix = FIXES.get(qid)
    return fix['now'] if fix else gold

def fingerprint(cfg):
    return hashlib.sha256(json.dumps([cfg, PROMPT], sort_keys=True).encode()).hexdigest()[:12]

def ask(cfg, question, seed):
    body = {'model': cfg['model'], 'stream': False, 'think': cfg['think'], 'keep_alive': '30m',
            'messages': [{'role': 'user', 'content': PROMPT.format(question=question)}],
            'options': {'seed': seed, 'num_ctx': cfg.get('num_ctx', 32768), 'num_predict': cfg['num_predict']}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return json.load(r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True, choices=CONFIGS)
    ap.add_argument('--split', default='dev', choices=['dev', 'test'])
    ap.add_argument('--sets', default='gsm8k,math')
    ap.add_argument('--limit', type=int, default=0, help='only the first N questions of each set (smoke tests)')
    ap.add_argument('--repeats', type=int, default=1,
                    help='independent runs per question with different seeds; averages out luck on small sets like AIME')
    a = ap.parse_args()
    cfg, fp = CONFIGS[a.config], fingerprint(CONFIGS[a.config])

    out = ROOT / 'results' / a.config / f'{a.split}.jsonl'
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for row in map(json.loads, out.read_text().splitlines()):
            if row['fingerprint'] != fp:
                sys.exit(f'{out} was made with a different recipe or prompt. Use a new config name instead of editing one.')
            done.add((row['id'], row['sample'], row.get('repeat', 0)))

    items = []
    for s in a.sets.split(','):
        rows = [json.loads(l) for l in (ROOT / 'data' / f'{s}_{a.split}.jsonl').read_text().splitlines()]
        items += rows[:a.limit] if a.limit else rows
    todo = [(it, k, rp) for rp in range(a.repeats) for it in items for k in range(cfg['samples'])
            if (it['id'], k, rp) not in done]

    if a.split == 'test' and todo:
        with open(ROOT / 'results' / 'TEST_LEDGER.md', 'a') as f:
            f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} test run: config `{a.config}` ({fp}), sets {a.sets}, "
                    f"{len(todo)} answers to do, repeats {a.repeats}{' (limit ' + str(a.limit) + ')' if a.limit else ''}\n")

    print(f'{a.config} on {a.split}: {len(todo)} answers to do, {len(done)} already done', flush=True)
    right = n = 0
    t0 = time.time()
    with open(out, 'a') as f:
        for i, (it, k, rp) in enumerate(todo, 1):
            seed = zlib.crc32(f"{it['id']}-{k}".encode() + (f'-r{rp}'.encode() if rp else b''))
            started = time.time()
            try:
                r = ask(cfg, it['question'], seed)
            except Exception as e:  # leave it undone so a rerun retries it
                print(f"  ! {it['id']}: {e}", flush=True)
                continue
            content = r.get('message', {}).get('content', '')
            gold = gold_for(it['id'], it['answer'])
            ok, extracted, unsure = grade(content, gold, it['set'])
            row = {'id': it['id'], 'set': it['set'], 'level': it.get('level'), 'sample': k, 'repeat': rp, 'gold': gold,
                   'extracted': extracted, 'correct': ok, 'unsure': unsure,
                   'tokens': r.get('eval_count'), 'seconds': round(time.time() - started, 1),
                   'truncated': r.get('done_reason') == 'length', 'thinking_chars': len(r.get('message', {}).get('thinking') or ''),
                   'thinking': r.get('message', {}).get('thinking') or '',
                   'content': content, 'config': a.config, 'fingerprint': fp}
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            f.flush()
            n += 1; right += ok
            eta = (time.time() - t0) / i * (len(todo) - i) / 60
            print(f"  {i}/{len(todo)} {it['id']}: {'✓' if ok else '✗'} {str(extracted)[:30]!r} (gold {it['answer'][:30]!r}) "
                  f"{row['tokens']} tok {row['seconds']}s | {right}/{n} so far, ~{eta:.0f} min left", flush=True)

if __name__ == '__main__':
    main()
