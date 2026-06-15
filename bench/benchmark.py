# -*- coding: utf-8 -*-
"""Benchmark pequeño: calcular valores a N cifras correctas.

Competidores (precisión arbitraria en Python):
  - cabal   : real exacto perezoso, CERTIFICADO, cero dependencias
  - mpmath  : float de precisión arbitraria (fijas dps y confías)
  - decimal : stdlib (solo sqrt/exp/ln; sin pi ni sin)
  - sympy   : simbólico, N(expr, d) (usa mpmath por dentro)

Nota de equidad: mpmath cachea pi y e. La columna mpmath de pi/e se mide con
la caché invalidada por precisión, de modo que usa su algoritmo NATIVO (no la
ruta lenta 4*atan(1)). Es la comparación honesta "cómputo desde cero".

Uso:  pip install mpmath sympy  &&  python bench/benchmark.py   (raíz del repo)
"""
import sys, os
from time import perf_counter
from decimal import Decimal, getcontext

import mpmath as mp
import sympy as sp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import cabal
from cabal import R, PI, E, LN2, raiz, exp, ln, sen

print("cabal", cabal.__version__, "| mpmath", mp.__version__,
      "| sympy", sp.__version__, "| python", sys.version.split()[0])
GUARD = 20

def timed(fn, reps):
    best = float('inf')
    for _ in range(reps):
        t0 = perf_counter()
        fn()
        dt = perf_counter() - t0
        if dt < best:
            best = dt
    return best

# --- cómo calcula cada librería el valor a N cifras ---
def cabal_fn(task, N):
    e = {'pi': PI, 'e': E, 'sqrt2': raiz(2), 'ln2': LN2, 'sin1': sen(1)}[task]
    return lambda: e.decimales(N)

# nonce para invalidar la caché de constantes de mpmath (pi/e) y forzar recómputo
_n = [0]
def mpmath_fn(task, N):
    def run():
        _n[0] = (_n[0] + 1) % 3
        mp.mp.dps = N + GUARD + _n[0]
        v = {'pi':   lambda: +mp.pi,          # algoritmo nativo (Chudnovsky)
             'e':    lambda: +mp.e,
             'sqrt2':lambda: mp.sqrt(2),
             'ln2':  lambda: mp.log(2),
             'sin1': lambda: mp.sin(1)}[task]()
        return mp.nstr(v, N + 2)
    return run

def decimal_fn(task, N):
    if task in ('pi', 'sin1'):
        return None                          # decimal no trae pi ni sin
    def run():
        getcontext().prec = N + GUARD
        v = {'e':    lambda: Decimal(1).exp(),
             'sqrt2':lambda: Decimal(2).sqrt(),
             'ln2':  lambda: Decimal(2).ln()}[task]()
        return str(v)
    return run

def sympy_fn(task, N):
    expr = {'pi': sp.pi, 'e': sp.E, 'sqrt2': sp.sqrt(2),
            'ln2': sp.log(2), 'sin1': sp.sin(1)}[task]
    return lambda: str(sp.N(expr, N + 2))

LIBS = [('cabal', cabal_fn), ('mpmath', mpmath_fn),
        ('decimal', decimal_fn), ('sympy', sympy_fn)]
TASKS = ['pi', 'e', 'sqrt2', 'ln2', 'sin1']
NS = [100, 1000, 5000]
REPS = {100: 25, 1000: 6, 5000: 2}

# verificación de corrección (primeras 40 cifras coinciden cabal vs mpmath)
print("\n[corrección] primeras 40 cifras cabal == mpmath:")
for task in TASKS:
    c = cabal_fn(task, 50)()
    m = mpmath_fn(task, 50)()
    same = c[:42] == m[:42]
    print(f"  {task:6s} {'OK' if same else 'DIFIERE'}  {c[:42]}")

for N in NS:
    reps = REPS[N]
    print(f"\n================  N = {N} cifras   (mejor de {reps})  ================")
    header = f"{'tarea':7s}" + "".join(f"{l:>12s}" for l, _ in LIBS) + \
             f"{'cabal vs mejor':>16s}"
    print(header)
    print("-" * len(header))
    for task in TASKS:
        row = f"{task:7s}"
        times = {}
        for lib, factory in LIBS:
            fn = factory(task, N)
            if fn is None:
                row += f"{'--':>12s}"
                continue
            r = 1 if (lib == 'sympy' and N >= 5000) else reps
            try:
                dt = timed(fn, r)
                times[lib] = dt
                row += f"{dt*1000:>11.2f}m"
            except Exception:
                row += f"{'ERR':>12s}"
        others = {k: v for k, v in times.items() if k != 'cabal'}
        if 'cabal' in times and others:
            ratio = times['cabal'] / min(others.values())
            row += f"{ratio:>13.2f}x"
        print(row)

print("\n(ms = milisegundos, mejor de N corridas. 'cabal vs mejor' < 1 = cabal más rápido)")
