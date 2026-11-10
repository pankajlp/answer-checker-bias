"""Freeze the dev/test splits once. Re-running produces the same files (fixed seed) and refuses to
overwrite splits whose contents changed, so the test set can't drift."""
import hashlib, json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / 'data' / 'raw', ROOT / 'data'
SEED, DEV, TEST = 2026, 60, 150

def gsm8k():
    for i, line in enumerate(open(RAW / 'gsm8k_test.jsonl')):
        r = json.loads(line)
        ans = r['answer'].split('####')[-1].strip().replace(',', '')
        yield {'id': f'gsm8k-{i:04d}', 'set': 'gsm8k', 'question': r['question'], 'answer': ans}

def math500():
    for r in map(json.loads, open(RAW / 'math500_test.jsonl')):
        yield {'id': 'math-' + re.sub(r'[^A-Za-z0-9]+', '_', r['unique_id']).strip('_'), 'set': 'math',
               'question': r['problem'], 'answer': r['answer'], 'subject': r['subject'], 'level': r['level']}

def aime(year):
    rows = json.load(open(RAW / f'aime_{year}.json'))['rows']
    for r in (x['row'] for x in rows):
        yield {'id': f"aime{year}-{r['problem_idx']:02d}", 'set': 'aime', 'question': r['problem'], 'answer': str(r['answer'])}

def main():
    hashes = {}
    for name, rows in (('gsm8k', list(gsm8k())), ('math', list(math500()))):
        random.Random(f'{SEED}-{name}').shuffle(rows)
        for split, part in (('dev', rows[:DEV]), ('test', rows[DEV:DEV + TEST])):
            text = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in sorted(part, key=lambda r: r['id']))
            path = OUT / f'{name}_{split}.jsonl'
            if path.exists() and path.read_text() != text:
                sys.exit(f'{path.name} already exists with different contents; refusing to change a frozen split.')
            path.write_text(text)
            hashes[path.name] = hashlib.sha256(text.encode()).hexdigest()
            print(f'{path.name}: {len(part)} questions')
    # AIME is too small to split at random: 2025 is dev, 2026 (newest, least likely to be in training data) is test
    for split, year in (('dev', 2025), ('test', 2026)):
        text = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in aime(year))
        path = OUT / f'aime_{split}.jsonl'
        if path.exists() and path.read_text() != text:
            sys.exit(f'{path.name} already exists with different contents; refusing to change a frozen split.')
        path.write_text(text)
        hashes[path.name] = hashlib.sha256(text.encode()).hexdigest()
        print(f'{path.name}: {text.count(chr(10))} questions')
    (OUT / 'SPLITS.sha256').write_text(''.join(f'{h}  {n}\n' for n, h in sorted(hashes.items())))

if __name__ == '__main__':
    main()
