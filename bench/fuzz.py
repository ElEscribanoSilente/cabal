# -*- coding: utf-8 -*-
"""Fuzz diferencial: árboles de expresión aleatorios; el valor de mpmath
debe caer SIEMPRE dentro del cerco certificado de cabal. Si alguno se sale,
cabal habría violado su contrato. Determinista (semilla fija).

Uso:  pip install mpmath  &&  python bench/fuzz.py   (desde la raíz del repo)
"""
import sys, os, random
from fractions import Fraction
from decimal import Decimal, getcontext
import mpmath as mp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import cabal
from cabal import R, raiz, exp, ln, sen, cos, atan, Inseparables

mp.mp.dps = 120
getcontext().prec = 400
random.seed(1234)

N = 4000
BITS = 110          # ancho de cerco ~ 2^-109 ~ 1.5e-33
SIG = 90            # cifras del oráculo (>> ancho del cerco)

def rand_real(depth):
    """(expr_cabal, mpf_value) o None si toca dominio inválido/inseparable."""
    if depth <= 0 or random.random() < 0.3:
        num = random.randint(-20, 20)
        den = random.randint(1, 12)
        fr = Fraction(num, den)
        return R(fr), mp.mpf(num) / den
    op = random.choice(
        ['+','-','*','/','exp','ln','sen','cos','atan','raiz','sq'])
    a = rand_real(depth-1)
    if a is None:
        return None
    ea, va = a
    if op in ('+','-','*','/'):
        b = rand_real(depth-1)
        if b is None:
            return None
        eb, vb = b
        if op == '+':
            return ea+eb, va+vb
        if op == '-':
            return ea-eb, va-vb
        if op == '*':
            return ea*eb, va*vb
        if op == '/':
            if vb == 0 or abs(vb) < mp.mpf('1e-6'):
                return None
            return ea/eb, va/vb
    if op == 'exp':
        if abs(va) > 60:            # evita magnitudes absurdas
            return None
        return exp(ea), mp.e**va
    if op == 'ln':
        if va <= mp.mpf('1e-6'):
            return None
        return ln(ea), mp.log(va)
    if op == 'sen':
        if abs(va) > 300:
            return None
        return sen(ea), mp.sin(va)
    if op == 'cos':
        if abs(va) > 300:
            return None
        return cos(ea), mp.cos(va)
    if op == 'atan':
        return atan(ea), mp.atan(va)
    if op == 'raiz':
        if va < 0:
            return None
        return raiz(ea), mp.sqrt(va)
    if op == 'sq':
        return ea*ea, va*va

def ofrac(v):
    with mp.workdps(SIG + 25):
        return Fraction(Decimal(mp.nstr(v, SIG, strip_zeros=False)))

tested = skipped = viol = 0
errs = 0
for i in range(N):
    r = rand_real(depth=random.randint(1, 4))
    if r is None:
        skipped += 1
        continue
    expr, val = r
    if not mp.isfinite(val) or abs(val) > mp.mpf('1e60'):
        skipped += 1
        continue
    try:
        lo, hi = expr.intervalo(BITS)
        o = ofrac(val)
        tested += 1
        if not (lo <= o <= hi):
            viol += 1
            if viol <= 10:
                print(f"  VIOLACIÓN #{i}: o={float(o):.6e} "
                      f"lo={float(lo):.6e} hi={float(hi):.6e}")
    except Inseparables:
        skipped += 1
    except (ValueError, ZeroDivisionError):
        skipped += 1
    except Exception as e:
        errs += 1
        if errs <= 10:
            print(f"  ERROR INESPERADO #{i}: {type(e).__name__}: {e}")

print(f"fuzz: {tested} verificados, {skipped} omitidos (dominio/inseparable), "
      f"{viol} violaciones de contrato, {errs} errores inesperados")
if viol or errs:
    print("FALLO")
    sys.exit(1)
print("TODO OK: el valor verdadero cayó SIEMPRE dentro del cerco certificado.")
