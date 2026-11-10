"""Answer checking for GSM8K and MATH-500. Standard library only.

grade(prediction_text, gold) -> (correct: bool, extracted: str|None, unsure: bool)
`unsure` marks cases the checker could not decide confidently (worth a human look)."""
import ast, cmath, math, operator, random, re

# ---------- extracting the final answer ----------

def last_boxed(text):
    """Contents of the last \\boxed{...} or \\fbox{...}, with nested braces handled."""
    idx = max(text.rfind('\\boxed'), text.rfind('\\fbox'))
    if idx < 0:
        return None
    i = text.find('{', idx)
    if i < 0:  # \boxed 5
        m = re.match(r'\\(?:boxed|fbox)\s+([^\s$]+)', text[idx:])
        return m.group(1) if m else None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    return None

def extract(text, kind):
    text = text or ''
    b = last_boxed(text)
    if b is not None:
        return b, 'boxed'
    if kind == 'gsm8k':  # fallback: "answer is X" or the last number
        m = re.findall(r'answer\s*(?:is|:)\s*\$?\s*(-?[\d,]*\.?\d+)', text, re.I) or \
            re.findall(r'-?\d[\d,]*\.?\d*', text)
        if m:
            return m[-1], 'fallback'
    return None, 'none'

# ---------- normalising ----------

def _strip_text(s):
    return re.sub(r'\\(?:text|textbf|mathrm|mbox|textnormal)\s*\{([^{}]*)\}', r'\1', s)

def normalize(s):
    s = s.strip()
    s = re.sub(r'\\(?:left|right|displaystyle|big|Big|bigg|Bigg)(?![a-zA-Z])', '', s)
    s = s.replace('\\!', '').replace('\\,', '').replace('\\;', '').replace('\\:', '')
    s = re.sub(r'(?<!\\)\\ ', ' ', s)
    s = s.replace('\\$', '').replace('$', '')
    s = s.replace('\\dfrac', '\\frac').replace('\\tfrac', '\\frac')
    s = re.sub(r'\^\s*\{?\s*\\circ\s*\}?', '', s).replace('°', '')
    s = s.replace('\\%', '').replace('%', '')
    s = _strip_text(s)
    s = re.sub(r'\\\\\[[^\]]*\]', r'\\\\', s)                # matrix row spacing \\[6pt]
    if '=' in s and s.rsplit('=', 1)[1].strip():               # v = ... = answer: keep the last part
        s = s.rsplit('=', 1)[1]
    s = re.sub(r'^\s*[a-zA-Z]\s*\\in\s*', '', s)            # x \in [a,b]
    s = re.sub(r'\\frac\s*(\d)\s*(\d)', r'\\frac{\1}{\2}', s)      # \frac34
    s = re.sub(r'\\frac\s*(\d)\s*\{', r'\\frac{\1}{', s)           # \frac9{19}
    s = re.sub(r'\\frac\s*\{([^{}]*)\}\s*(\d)', r'\\frac{\1}{\2}', s)
    s = re.sub(r'\\sqrt\s*(\d+)', r'\\sqrt{\1}', s)
    def mixed(m):  # 137 \frac{1}{2} -> 137+1/2 ; -2\frac{1}{2} -> -(2+1/2)
        sign, whole, a, b = m.groups()
        if int(a) >= int(b):
            return m.group(0)
        body = f'{whole}+\\frac{{{a}}}{{{b}}}'
        return f'-({body})' if sign else body
    s = re.sub(r'(?<![\d.])(-?)(\d+)\s*\\frac\{(\d+)\}\{(\d+)\}', mixed, s)
    s = re.sub(r'(\d)\s*\^\s*\{?\s*(?:\\(?:mathrm|text)\s*\{)?\s*(?:st|nd|rd|th)\s*\}?\s*\}?', r'\1', s)  # 12^{\mathrm{th}}
    s = s.rstrip('.').strip()
    s = re.sub(r'\s+', '', s)
    if re.fullmatch(r'-?\d{1,3}(,\d{3})+(\.\d+)?', s):     # 58,500 -> 58500 (whole answer only)
        s = s.replace(',', '')
    if re.fullmatch(r'\(?[A-Ea-e]\)?', s):                # multiple choice (C)
        s = s.strip('()').upper()
    return s

def drop_units(s):
    """'5.4cents' -> '5.4', '12grade' -> '12' (normalised strings; words of 2+ letters only, so '3x' stays)."""
    m = re.fullmatch(r'(-?[\d.]+(?:\+\\frac\{\d+\}\{\d+\})?)(?:[a-zA-Z]{2,}\.?)+(?:\^\(?\d\)?)?', s)
    return m.group(1) if m else s

# ---------- evaluating LaTeX as numbers ----------

_FUNCS = {'sqrt': cmath.sqrt, 'sin': cmath.sin, 'cos': cmath.cos, 'tan': cmath.tan,
          'cot': lambda x: 1 / cmath.tan(x), 'sec': lambda x: 1 / cmath.cos(x), 'csc': lambda x: 1 / cmath.sin(x),
          'log': cmath.log, 'ln': cmath.log, 'exp': cmath.exp}
_CONST = {'pi': math.pi, 'e': math.e, 'i': 1j}
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}

def to_python(s):
    """Turn a normalised LaTeX expression into a Python expression string, or None."""
    if re.search(r'_|\\infty|\\cup|\\cap|\\begin|[<>]|\\le|\\ge|=', s):
        return None
    t = s
    for _ in range(10):  # nested fracs/sqrts/powers, innermost first
        t2 = re.sub(r'\^\{([^{}]*)\}', r'^(\1)', t)
        t2 = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'((\1)/(\2))', t2)
        t2 = re.sub(r'\\sqrt\[([^\]]*)\]\{([^{}]*)\}', r'((\2)**(1/(\1)))', t2)
        t2 = re.sub(r'\\sqrt\{([^{}]*)\}', r'sqrt(\1)', t2)
        if t2 == t:
            break
        t = t2
    t = t.replace('\\cdot', '*').replace('\\times', '*').replace('\\pi', 'pi').replace('{', '(').replace('}', ')')
    t = re.sub(r'\\(sin|cos|tan|cot|sec|csc|log|ln|exp)\s*([a-zA-Z0-9]+)', r'\1(\2)', t)
    t = re.sub(r'\\(sin|cos|tan|cot|sec|csc|log|ln|exp)', r'\1', t)
    if '\\' in t:
        return None
    t = t.replace('^', '**')
    # implicit multiplication: 3sqrt(2), 2pi, 3x, )(, x y
    names = sorted(list(_FUNCS) + ['pi'], key=len, reverse=True)
    tokens = re.findall(r'\d*\.\d+|\d+|' + '|'.join(names) + r'|[a-zA-Z]|\*\*|[-+*/()]', t)
    if ''.join(tokens) != t:
        return None
    out = []
    for k, tok in enumerate(tokens):
        if out:
            prev = out[-1]
            prev_val = re.fullmatch(r'[\d.]+|pi|[a-zA-Z]|\)', prev) and prev not in _FUNCS
            cur_val = re.fullmatch(r'[\d.]+|[a-zA-Z]+|\(', tok)
            if prev_val and cur_val:
                out.append('*')
        out.append(tok)
    return ''.join(out)

def safe_eval(expr, env):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100:
                raise ValueError('power too large')
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name) and n.id in env:
            return env[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and len(n.args) == 1:
            return _FUNCS[n.func.id](ev(n.args[0]))
        raise ValueError('unsupported')
    return complex(ev(ast.parse(expr, mode='eval')))

def free_vars(expr):
    return sorted(set(re.findall(r'[a-zA-Z]+', expr)) - set(_FUNCS) - {'pi', 'e', 'i'})

def num_equal(a, b):
    """Compare two expressions numerically; free variables get the same random values on both sides."""
    pa, pb = to_python(a), to_python(b)
    if pa is None or pb is None:
        return None
    va, vb = free_vars(pa), free_vars(pb)
    if va != vb:
        return None if (va or vb) else False
    rng = random.Random(0)
    try:
        for _ in range(3 if va else 1):
            env = dict(_CONST, **{v: rng.uniform(1.1, 2.9) for v in va})
            x, y = safe_eval(pa, env), safe_eval(pb, env)
            if abs(x - y) > 1e-6 * max(1.0, abs(y)):
                return False
        return True
    except (ValueError, ZeroDivisionError, OverflowError, SyntaxError, TypeError, RecursionError):
        return None

# ---------- structures: tuples, intervals, lists, matrices ----------

def split_top(s, sep=','):
    parts, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return parts

def matrix_entries(s):
    m = re.fullmatch(r'\\begin\{[pbv]?matrix\}(.*)\\end\{[pbv]?matrix\}', s)
    if not m:
        return None
    return [cell for row in m.group(1).split('\\\\') for cell in row.split('&') if cell != '']

def equal(pred, gold):
    """Returns True / False / None (couldn't decide)."""
    if pred == gold:
        return True
    if pred.lower() == gold.lower() and not re.search(r'\d', gold):
        return True
    base = re.fullmatch(r'([0-9A-Za-z]+)_\{?(\d+)\}?', gold)       # 4343_6: the base is in the question
    if base:
        pb = re.fullmatch(r'([0-9A-Za-z]+)(?:_\{?(\d+)\}?)?', pred)
        return bool(pb) and pb.group(1).lower() == base.group(1).lower() and pb.group(2) in (None, base.group(2))
    mp, mg = matrix_entries(pred), matrix_entries(gold)
    if mg is not None:
        if mp is None or len(mp) != len(mg):
            return False
        return all_equal(mp, mg)
    if '\\cup' in gold or '\\cup' in pred:
        gp, pp = gold.split('\\cup'), pred.split('\\cup')
        return len(gp) == len(pp) and all_equal(pp, gp)
    bracket = re.fullmatch(r'([(\[])(.*)([)\]])', gold)
    if bracket and ',' in bracket.group(2) and len(split_top(bracket.group(2))) > 1:
        pb = re.fullmatch(r'([(\[])(.*)([)\]])', pred)
        if not pb or (pb.group(1), pb.group(3)) != (bracket.group(1), bracket.group(3)):
            return False
        gi, pi_ = split_top(bracket.group(2)), split_top(pb.group(2))
        return len(gi) == len(pi_) and all_equal(pi_, gi)
    gparts = split_top(gold)
    if len(gparts) > 1:  # unordered list of answers
        pparts = split_top(pred)
        if len(pparts) != len(gparts):
            return False
        remaining = list(pparts)
        for g in gparts:
            hit = next((p for p in remaining if equal(p, g)), None)
            if hit is None:
                return False
            remaining.remove(hit)
        return True
    if '\\infty' in gold or '\\infty' in pred:
        return pred.replace('+\\infty', '\\infty') == gold.replace('+\\infty', '\\infty')
    return num_equal(pred, gold)

def all_equal(ps, gs):
    results = [equal(p, g) for p, g in zip(ps, gs)]
    if any(r is False for r in results):
        return False
    return None if any(r is None for r in results) else True

# ---------- public ----------

def grade(text, gold, kind):
    raw, how = extract(text, kind)
    if raw is None:
        return False, None, False
    g = normalize(gold)
    p = normalize(raw)
    result = equal(p, g)
    if result is not True:
        pu, gu = drop_units(p), drop_units(g)
        if (pu, gu) != (p, g) and equal(pu, gu) is True:
            return True, raw, how == 'fallback'
    if result is None:  # undecidable: fall back to strict string match but flag it
        return False, raw, True
    return result, raw, how == 'fallback'
