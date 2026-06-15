# -*- coding: utf-8 -*-
"""Regresión: __float__ debe devolver SIEMPRE el double más cercano (ties-to-even).

Bug corregido en 0.2.1: antes había doble redondeo y float(x) podía quedar a 1 ULP
del valor correcto (~2.8% de racionales, ~5.7% de opacos). Oráculos:
  - racionales: float(Fraction) de CPython (correctamente redondeado).
  - opacos:     float(mpmath a alta precisión).

Uso:  pip install mpmath  &&  python bench/float_redondeo.py   (raíz del repo)
"""
import sys, os, random, math
from fractions import Fraction
import mpmath as mp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import cabal
from cabal import R, exp, ln, raiz, sen, cos, atan

print("cabal", cabal.__version__, "| mpmath", mp.__version__)
mp.mp.dps = 60
random.seed(12345)

bad_rat = bad_op = tot_rat = tot_op = worse = 0
ejemplos = []

# ---------- A) racionales (oráculo perfecto: float(Fraction)) ----------
N = 300000
for _ in range(N):
    if random.random() < 0.5:
        man = random.getrandbits(60) | 1          # mantisa impar -> >53 bits sig.
        q = Fraction(man) * Fraction(2) ** random.randint(-1080, 1000)
    else:
        q = Fraction(random.randint(-(2**62), 2**62), 2 ** random.randint(0, 90))
    try:
        ref = float(q)
    except OverflowError:
        continue
    tot_rat += 1
    got = float(R(q))
    if got != ref:
        bad_rat += 1
        if math.nextafter(got, ref) != ref:
            worse += 1
        if len(ejemplos) < 4:
            ejemplos.append((str(q), got, ref))

# ---------- B) opacos (oráculo: float(mpmath)) ----------
M = 40000
for _ in range(M):
    a = Fraction(random.randint(-30, 30), random.randint(1, 9))
    fa = float(a); mv = mp.mpf(a.numerator) / a.denominator
    op = random.choice(['exp', 'ln', 'raiz', 'sen', 'cos', 'atan'])
    try:
        if   op == 'exp' and abs(fa) < 10: e, v = exp(a), mp.e ** mv
        elif op == 'ln'  and fa > 0:       e, v = ln(a),  mp.log(mv)
        elif op == 'raiz' and fa >= 0:     e, v = raiz(a), mp.sqrt(mv)
        elif op == 'sen':                  e, v = sen(a), mp.sin(mv)
        elif op == 'cos':                  e, v = cos(a), mp.cos(mv)
        elif op == 'atan':                 e, v = atan(a), mp.atan(mv)
        else: continue
    except Exception:
        continue
    with mp.workdps(60):
        ref = float(v)
    tot_op += 1
    got = float(e)
    if got != ref:
        bad_op += 1
        if math.nextafter(got, ref) != ref:
            worse += 1
        if len(ejemplos) < 8:
            ejemplos.append((f"{op}({a})", got, ref))

# ---------- casos límite construidos ----------
limites = [
    Fraction(2**53 + 1, 2**53),            # punto medio exacto (tie -> even)
    Fraction(2**53 + 1, 2**53) + Fraction(1, 2**54),
    Fraction(2**54 + 1, 2**54),
    Fraction(2**53 + 1),                   # entero en el filo de 2^53
    Fraction(2*(2**52) + 1) * Fraction(2) ** -1075,   # tie subnormal
    Fraction(-5, 2) ** 1,
]
for q in limites:
    tot_rat += 1
    if float(R(q)) != float(q):
        bad_rat += 1
        ejemplos.append((str(q) + " [limite]", float(R(q)), float(q)))

print(f"\nracionales: {bad_rat}/{tot_rat} incorrectos")
print(f"opacos    : {bad_op}/{tot_op} incorrectos")
print(f"peor que 1 ULP: {worse}")
if bad_rat or bad_op:
    print("\nFALLOS (muestra):")
    for q, got, ref in ejemplos[:10]:
        print(f"  {q}\n     got={got!r}  ref={ref!r}")
    sys.exit(1)
print("\nTODO OK: float() es ahora el double más cercano en todos los casos.")
