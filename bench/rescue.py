"""Rescue answers that ran out of room: for every saved answer that hit the token limit without a final
answer, show the model the end of its own reasoning and ask it to commit to an answer (thinking off,
short budget). Answers that finished are copied unchanged, so the result is a full configuration
named <base>-rescue that report.py can compare with <base>.

  python3 bench/rescue.py --base think --split dev"""
import argparse, datetime, hashlib, json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
from grader import grade
from run import OLLAMA, gold_for

TAIL_CHARS = 12000
RESCUE_TOKENS = 2000
RESCUE_PROMPT = ('Problem:\n{question}\n\n'
                 'You were solving this problem and ran out of time. Here is the end of your reasoning so far:\n'
                 '<<<\n{tail}\n>>>\n\n'
                 'Do not start over. Using the work above, give your best final answer now. '
                 'Briefly state how it follows, then put the final answer within \\boxed{{}}.')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--split', default='dev', choices=['dev', 'test'])
    a = ap.parse_args()
    src = ROOT / 'results' / a.base / f'{a.split}.jsonl'
    out = ROOT / 'results' / f'{a.base}-rescue' / f'{a.split}.jsonl'
    out.parent.mkdir(parents=True, exist_ok=True)
    base_rows = [json.loads(l) for l in src.read_text().splitlines()]
    questions = {}
    for f in (ROOT / 'data').glob(f'*_{a.split}.jsonl'):
        for r in map(json.loads, f.read_text().splitlines()):
            questions[r['id']] = r
    key = lambda r: (r['id'], r['sample'], r.get('repeat', 0))
    done = {key(r) for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
    model = None
    todo = [r for r in base_rows if key(r) not in done]
    need = [r for r in todo if r['truncated'] and r['extracted'] is None]
    if a.split == 'test' and need:
        with open(ROOT / 'results' / 'TEST_LEDGER.md', 'a') as f:
            f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} test run: rescue of `{a.base}`, {len(need)} answers to rescue\n")
    print(f'{len(todo)} answers to copy or rescue, {len(need)} need rescuing', flush=True)
    with open(out, 'a') as f:
        for r in todo:
            row = dict(r, config=f'{a.base}-rescue',
                       fingerprint=hashlib.sha256((r['fingerprint'] + RESCUE_PROMPT + str((TAIL_CHARS, RESCUE_TOKENS))).encode()).hexdigest()[:12])
            if r['truncated'] and r['extracted'] is None:
                reasoning = r.get('thinking') or r.get('content') or ''
                if not reasoning:
                    print(f"  ! {r['id']}: no saved reasoning to rescue from (run made before reasoning was saved)", flush=True)
                    continue
                q = questions[r['id']]
                body = {'model': 'qwen3.8:27b', 'stream': False, 'think': False, 'keep_alive': '30m',
                        'messages': [{'role': 'user', 'content': RESCUE_PROMPT.format(question=q['question'], tail=reasoning[-TAIL_CHARS:])}],
                        'options': {'seed': 7, 'num_ctx': 16384, 'num_predict': RESCUE_TOKENS}}
                t0 = time.time()
                req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=1800) as resp:
                    res = json.load(resp)
                text = res.get('message', {}).get('content', '')
                gold = gold_for(r['id'], r['gold'])
                ok, ex, un = grade(text, gold, r['set'])
                row.update(content=text, correct=ok, extracted=ex, unsure=un, rescued=True,
                           tokens=(r['tokens'] or 0) + (res.get('eval_count') or 0),
                           seconds=round(r['seconds'] + time.time() - t0, 1),
                           truncated=res.get('done_reason') == 'length')
                print(f"  rescued {r['id']} r{r.get('repeat', 0)}: {'✓' if ok else '✗'} {ex!r} (gold {gold!r})", flush=True)
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            f.flush()

if __name__ == '__main__':
    main()
