"""Auditoria adversarial, ronda 2: DAGs compartidos, recursion real, NaN, 10k digitos."""
import sys
import time
import random
from fractions import Fraction

import mpmath
from mpmath import mp, mpf

import cabal as cb
from cabal import R, PI, E, LN2, raiz, exp, ln, sen, cos, tan, atan, Inseparables

OK, FALLOS, AVISOS = 0, [], []


def caso(nombre, cond, extra=""):
    global OK
    if cond:
        OK += 1
    else:
        FALLOS.append(f"{nombre} {extra}")
        print(f"  X FALLO {nombre} {extra}")


def aviso(t):
    AVISOS.append(t)
    print(f"  ! aviso: {t}")


def zero_opaco():
    return raiz(R(2)) ** 2 - 2


# C1: DAG con nodos compartidos, precisiones entrelazadas, cache compartida
def c1_dag_compartido():
    rnd = random.Random(404)
    for i in range(60):
        f = Fraction(rnd.randint(-999, 999), rnd.randint(1, 99))
        x = R(f) + zero_opaco()              # opaco con valor f
        y = x * x + x                        # x compartido (2 padres)
        w = y - x * (x + 1)                  # = 0; x compartido 4 veces
        fy = f * f + f
        for p in (300, 5, -20, 800, 64, 5, 1000):
            caso("C1.dag_y", abs(Fraction(y.aprox(p)) - fy * Fraction(2) ** p) <= 1,
                 f"f={f} p={p}")
            caso("C1.dag_w", abs(w.aprox(p)) <= 1, f"f={f} p={p}")
            if p == 800:
                _ = x.aprox(2000)            # sube la cache del nodo compartido
        if i % 7 == 0 and f != 0:
            caso("C1.signo", (y * (1 + zero_opaco())).signo(tope=4096) ==
                 (1 if fy > 0 else (-1 if fy < 0 else 1)), f"f={f}")


# C2: recursion real con cadena OPACA profunda
def c2_recursion():
    x = zero_opaco()
    for _ in range(3000):
        x = x + 1
    try:
        m = x.aprox(0)
        caso("C2.cadena3000", abs(m - 3000) <= 1, f"m={m}")
    except RecursionError:
        aviso("cadena opaca de 3000 sumas: RecursionError en aprox(0) "
              "(limite de recursion de CPython; no documentado en README)")
        caso("C2.cadena3000", True)
    lim = sys.getrecursionlimit()
    sys.setrecursionlimit(100_000)
    try:
        t0 = time.time()
        m = x.aprox(0)
        dt = time.time() - t0
        caso("C2.cadena_limalta", abs(m - 3000) <= 1, f"m={m}")
        print(f"    cadena 3000 con setrecursionlimit: {dt:.2f}s "
              f"(precision interna crece +2 bits/nivel)")
    except RecursionError:
        caso("C2.cadena_limalta", False, "RecursionError incluso con limite 100k")
    finally:
        sys.setrecursionlimit(lim)


# C3: NaN / inf en comparaciones y construccion
def c3_nan():
    try:
        R(float("nan"))
        caso("C3.nan_R", False, "acepto NaN")
    except ValueError:
        caso("C3.nan_R", True)
    try:
        r = PI == float("nan")
        caso("C3.nan_eq", r is False, f"r={r}")
        if r is False:
            pass
    except ValueError:
        aviso("PI == float('nan') lanza ValueError (lo idiomatico seria False): "
              "_R(o) valida dentro de __eq__")
        caso("C3.nan_eq", True)
    try:
        PI < float("inf")
        caso("C3.inf_lt", True)
    except ValueError:
        aviso("PI < float('inf') lanza ValueError (orden vs inf no soportado)")
        caso("C3.inf_lt", True)


# C4: validacion a 10 000 digitos (claim del README) vs mpmath
def c4_diez_mil():
    sys.set_int_max_str_digits(2_000_000)
    with mpmath.workprec(34000):
        objetivos = [
            ("pi", PI, mpmath.pi),
            ("e", E, mpmath.e),
            ("ln2", LN2, mpmath.log(2)),
            ("sqrt2", raiz(2), mpmath.sqrt(2)),
            ("sen1", sen(R(1)), mpmath.sin(1)),
            ("exp_pi", exp(PI), mpmath.exp(mpmath.pi)),
        ]
        for nom, x, v in objetivos:
            t0 = time.time()
            d = x.decimales(10000)
            dt = time.time() - t0
            # oraculo: round(v*10^10000) con empates +inf, via mpmath.floor
            k = int(mpmath.floor(v * mpf(10) ** 10000 + mpf(1) / 2))
            s = "-" if k < 0 else ""
            k = abs(k)
            esperado = f"{s}{k // 10**10000}.{str(k % 10**10000).zfill(10000)}"
            caso(f"C4.{nom}", d == esperado, f"difiere (t={dt:.2f}s)")
            print(f"    {nom} a 10000 decimales: {dt:.2f}s")


# C5: contrato bajo aliasing extremo de potencias (_pot_ent comparte nodos)
def c5_potencias():
    rnd = random.Random(777)
    for _ in range(40):
        f = Fraction(rnd.randint(1, 99), rnd.randint(1, 99))
        x = R(f) + zero_opaco()
        n = rnd.choice((7, 12, 31, 64))
        y = x ** n
        fy = f ** n
        for p in (0, 100, -50):
            caso("C5.pow", abs(Fraction(y.aprox(p)) - fy * Fraction(2) ** p) <= 1,
                 f"f={f} n={n} p={p}")


def c5b_potencias_neg():
    rnd = random.Random(778)
    for _ in range(30):
        f = Fraction(rnd.randint(1, 99), rnd.randint(1, 99))
        x = R(f) + zero_opaco()
        n = -rnd.choice((1, 3, 9))
        y = x ** n
        fy = f ** n
        for p in (0, 100):
            caso("C5b.pow_neg", abs(Fraction(y.aprox(p)) - fy * Fraction(2) ** p) <= 1,
                 f"f={f} n={n} p={p}")


if __name__ == "__main__":
    for t in (c1_dag_compartido, c2_recursion, c3_nan, c4_diez_mil,
              c5_potencias, c5b_potencias_neg):
        print(t.__name__)
        t0 = time.time()
        t()
        print(f"  ({time.time() - t0:.1f}s)")
    print(f"\n{OK} OK, {len(FALLOS)} fallos, {len(AVISOS)} avisos")
    for a in AVISOS:
        print(f"  aviso: {a}")
    if FALLOS:
        sys.exit(1)
