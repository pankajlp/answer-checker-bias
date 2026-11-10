import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
from grader import grade

def g(pred, gold, kind='math'):
    return grade(f'blah blah \\boxed{{{pred}}}', gold, kind)[0]

class Grader(unittest.TestCase):
    def test_every_gold_matches_itself(self):
        for f in ROOT.glob('data/*_*.jsonl'):
            for r in map(json.loads, f.read_text().splitlines()):
                with self.subTest(id=r['id'], gold=r['answer']):
                    self.assertTrue(g(r['answer'], r['answer'], r['set']))

    def test_equivalent_forms(self):
        cases = [('0.5', '\\frac{1}{2}'), ('\\dfrac{3}{4}', '\\frac 34'), ('9/19', '\\frac9{19}'),
                 ('137.5', '137 \\frac{1}{2}'), ('58500', '58,500'), ('75', '75^\\circ'), ('75^{\\circ}', '75^\\circ'),
                 ('(3, \\frac{\\pi}{2})', '\\left( 3, \\frac{\\pi}{2} \\right)'), ('x=5', '5'), ('-q+p', 'p - q'),
                 ('3\\sqrt{13}', '3\\sqrt{13}'), ('\\sqrt{117}', '3\\sqrt{13}'), ('2+1i', '1+2i') , ('C', '\\text{(C)}'),
                 ('(C)', '\\text{(C)}'), ('Ellipse', '\\text{ellipse}'), ('[-2, 7]', 'x \\in [-2,7]'),
                 ('5.4', '5.4 \\text{ cents}'), ('11111111100', '11,\\! 111,\\! 111,\\! 100'), ('0.0000672', '.0000672'),
                 ('3, 1, 2', '1, 2, 3'), ('\\frac{\\pi^2}{8}', '\\frac{\\pi^2}{8}'), ('(b+2)(a+5)', '(a+5)(b+2)'),
                 ('\\begin{pmatrix} -\\frac13 \\\\ \\frac23 \\\\ \\frac53 \\end{pmatrix}', '\\begin{pmatrix} -1/3 \\\\ 2/3 \\\\ 5/3 \\end{pmatrix}'),
                 ('(5, \\infty)', '(5,\\infty)'), ('-\\pi/6', '-\\frac{\\pi}{6}'), ('11+11\\sqrt5', '11 \\sqrt{5} + 11'),
                 ('16\\sqrt3', '16 \\sqrt{3}'), ('137\\frac{1}{2}', '137 \\frac{1}{2}'), ('137\\frac12', '137.5'), ('4343', '4343_6'), ('\\left[\\dfrac{\\pi^{2}}{8},\\;\\dfrac{5\\pi^{2}}{4}\\right]', '\\left[ \\frac{\\pi^2}{8}, \\frac{5 \\pi^2}{4} \\right]'),
                 ('\\mathbf{v} = \\begin{pmatrix} -\\dfrac{1}{3} \\\\[6pt] \\dfrac{2}{3} \\\\[6pt] \\dfrac{5}{3} \\end{pmatrix}', '\\begin{pmatrix} -1/3 \\\\ 2/3 \\\\ 5/3 \\end{pmatrix}'),
                 ('\\frac{8}{49}\\begin{pmatrix} 2 \\\\ 6 \\\\ 3 \\end{pmatrix} = \\begin{pmatrix} 16/49 \\\\ 48/49 \\\\ 24/49 \\end{pmatrix}', '\\begin{pmatrix} 16/49 \\\\ 48/49 \\\\ 24/49 \\end{pmatrix}'),
                 ('y = 2x+3', 'y=2x+3'), ('4343_{6}', '4343_6'), ('-2\\frac{1}{2}', '-2.5'),
                 ('12^{\\mathrm{th}} \\text{ grade}', '12'), ('3\\frac{\\pi}{2}', '\\frac{3\\pi}{2}'), ('\\$18', '18'), ('18 dollars', '18'), ('1,000', '1000')]
        cases = [c for c in cases if c != ('2+1i', '1+2i')]
        for pred, gold in cases:
            with self.subTest(pred=pred, gold=gold):
                self.assertTrue(g(pred, gold), (pred, gold))

    def test_wrong_answers_rejected(self):
        cases = [('3', '4'), ('3\\frac{5}{2}', '3.5'), ('3x', '3'), ('3 x', '3'), ('\\frac{1}{3}', '\\frac{1}{2}'), ('(3,4)', '(3,4]'), ('(-1,6)', '(6,-1)'),
                 ('1+2i', '1-2i'), ('p+q', 'p - q'), ('40_8', '40_9'), ('4344', '4343_6'), ('x = 4', '5'), ('B', '\\text{(C)}'), ('1, 2', '1, 2, 3'),
                 ('[-2,7)', 'x \\in [-2,7]'), ('2\\sqrt{13}', '3\\sqrt{13}'), ('(-\\infty, 0)', '(-\\infty, 0]'),
                 ('x^5+x^4', 'x^5 - x^4 + x^3 - x^2 + x - 1'), ('\\begin{pmatrix} 1 \\\\ 0 \\end{pmatrix}', '\\begin{pmatrix} -1 & 0 \\\\ 0 & -1 \\end{pmatrix}')]
        for pred, gold in cases:
            with self.subTest(pred=pred, gold=gold):
                self.assertFalse(g(pred, gold), (pred, gold))

    def test_extraction(self):
        self.assertEqual(grade('So \\boxed{\\frac{1}{2}} is it', '\\frac12', 'math')[1], '\\frac{1}{2}')
        self.assertTrue(grade('first \\boxed{3} then corrected \\boxed{4}', '4', 'math')[0])
        self.assertFalse(grade('no box here 4', '4', 'math')[0])            # MATH requires a box
        ok, raw, unsure = grade('The answer is $18.', '18', 'gsm8k')          # GSM8K falls back to the number
        self.assertTrue(ok); self.assertTrue(unsure)

if __name__ == '__main__':
    unittest.main()
