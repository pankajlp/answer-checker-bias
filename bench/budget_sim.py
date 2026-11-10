"""What would Qwen Chat's thinking budget + rescue do? Simulated on saved dev answers (AIME 2025, think ×4).

  python3 bench/budget_sim.py 8000 16000 32000

For each budget B: an answer that finished within B tokens keeps its verdict. One that didn't is cut at B tokens
(its reasoning cut in proportion) and then either
  - left without an answer (no rescue: what the app did before), or
  - rescued with the app's exact rescue prompt (js/chat.js rescueMessages), thinking off, 2,000 tokens.
Thinking time is estimated from each answer's own speed. Dev only; writes results/budget_sim/dev.jsonl (resumable)."""
import json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
from grader import grade
from run import OLLAMA, PROMPT

TAIL = 12000
APP_RESCUE = ('{q}\n\nYou were working on this and ran out of thinking time. Here is the end of your reasoning so far:\n<<<\n{tail}\n>>>\n\n'
              'Do not start over. Using the work above, give your best final answer now: briefly say how it follows, then state the answer clearly. '
              'If the reasoning had not reached an answer, give your best estimate and say it is unconfirmed.')

def rescue(question, thinking):
    body = {'model': 'qwen3.8:27b', 'stream': False, 'think': False, 'keep_alive': '30m',
            'messages': [{'role': 'user', 'content': APP_RESCUE.format(q=PROMPT.format(question=question), tail=thinking[-TAIL:])}],
            'options': {'seed': 7, 'num_ctx': 16384, 'num_predict': 2000}}
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(OLLAMA, json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800) as r:
        res = json.load(r)
    return res['message']['content'], time.time() - t0

def main():
    budgets = [int(b) for b in sys.argv[1:]] or [8000, 16000, 32000]
    rows = [r for r in map(json.loads, open(ROOT / 'results/think/dev.jsonl')) if r['set'] == 'aime']
    qs = {q['id']: q for q in map(json.loads, open(ROOT / 'data/aime_dev.jsonl'))}
    out = ROOT / 'results/budget_sim/dev.jsonl'
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {(d['id'], d['repeat'], d['budget']): d for d in map(json.loads, out.read_text().splitlines())} if out.exists() else {}
    with open(out, 'a') as f:
        for B in budgets:
            for r in rows:
                k = (r['id'], r['repeat'], B)
                if k in done:
                    continue
                tps = r['tokens'] / r['seconds']
                if r['tokens'] < B and not r['truncated']:
                    d = {'kept': True, 'plain_ok': r['correct'], 'rescue_ok': r['correct'], 'secs_plain': r['seconds'], 'secs_rescue': r['seconds']}
                else:
                    cut = r['thinking'][: int(len(r['thinking']) * min(1, B / r['tokens']))]
                    text, rs = rescue(qs[r['id']]['question'], cut)
                    ok, ex, _ = grade(text, r['gold'], 'aime')
                    if ex is None:  # no \boxed{}: accept a clearly stated final number, as a reader would
                        ok, ex, _ = grade(text, r['gold'], 'gsm8k')
                    d = {'kept': False, 'plain_ok': False, 'rescue_ok': ok, 'rescued_answer': ex, 'secs_plain': B / tps,
                         'secs_rescue': B / tps + rs, 'rescue_text': text[-400:]}
                    print(f"  B={B} {r['id']} r{r['repeat']}: {'✓' if ok else '✗'} {ex!r} (gold {r['gold']}) {rs:.0f}s", flush=True)
                d.update(id=r['id'], repeat=r['repeat'], budget=B)
                done[k] = d
                f.write(json.dumps(d) + '\n'); f.flush()
    print(f"\n{'budget':>8} {'no rescue':>10} {'rescue':>8} {'gain':>6} {'cut off':>8} {'avg min':>8}")
    for B in budgets:
        ds = [done[(r['id'], r['repeat'], B)] for r in rows]
        n = len(ds)
        p, q = sum(d['plain_ok'] for d in ds), sum(d['rescue_ok'] for d in ds)
        print(f"{B:>8} {100*p/n:>9.1f}% {100*q/n:>7.1f}% {100*(q-p)/n:>+5.1f} {sum(not d['kept'] for d in ds):>8} "
              f"{sum(d['secs_rescue'] for d in ds)/n/60:>8.1f}")

if __name__ == '__main__':
    main()
