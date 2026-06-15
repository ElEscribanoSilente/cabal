"""Estres adversarial de cabal: el objetivo es HACERLA CHOCAR.

Secciones:
  S1 bombas (subprocesos con timeout): torres de exp, strings 1eN, precision 2M bits,
     cadenas de 100k nodos, tope=inf
  S2 protocolo Python: operandos desconocidos, __radd__ ajeno, tipos hostiles
  S3 entradas hostiles: strings raras a R(), p/n/tope de tipos invalidos, TOPE roto
  S4 concurrencia: 4 hilos martillando un DAG compartido (lib declarada NO thread-safe)
  S5 blast trascendente: arboles aleatorios espejados en mpmath, contrato a 300 bits
  S6 escala: pi/e/sqrt/exp a decenas de miles de digitos, x**10^6, aprox(-10^7)
Correr: python stress_cabal.py   (salida ASCII)
"""
import subprocess
import sys
import threading
import time
import random
from fractions import Fraction

import mpmath
from mpmath import mpf

import cabal as cb
from cabal import R, PI, E, LN2, raiz, exp, ln, sen, cos, tan, atan, Inseparables

RES = []          # (etiqueta, veredicto, detalle)
BUGS = []


def reg(et, veredicto, detalle=""):
    RES.append((et, veredicto, detalle))
    print(f"  [{veredicto}] {et}" + (f" -- {detalle}" if detalle else ""))
    if veredicto == "BUG":
        BUGS.append(f"{et}: {detalle}")


def zero_opaco():
    return raiz(R(2)) ** 2 - 2


# ---------------- S1: bombas en subproceso ----------------

PRE = "import cabal as cb\nfrom cabal import *\nz = raiz(R(2))**2 - 2\n"

BOMBAS = [
    ("torre exp(exp(exp(3))).aprox(0)",
     "x = exp(exp(exp(3)))\nprint(x.aprox(0))", 8),
    ("torre exp(exp(exp(exp(3)))) construir",
     "x = exp(exp(exp(exp(3))))\nprint('construido')", 8),
    ("R('1e100000000')",
     "x = R('1e100000000')\nprint('ok')", 8),
    ("PI.aprox(2_000_000)  (~600k digitos)",
     "print(PI.aprox(2_000_000) % 1000)", 10),
    ("cadena opaca de 100_000 sumas",
     "x = z\nfor _ in range(100_000): x = x + 1\nprint(x.aprox(0))", 30),
    ("signo(tope=float('inf')) de cero opaco",
     "print(z.signo(tope=float('inf')))", 10),
    ("1/(10^-100000 + opaco)  (msd > TOPE)",
     "x = 1/(R(10)**-100000 + z)\nprint(x.aprox(10))", 15),
]


def s1_bombas():
    for et, cuerpo, tmo in BOMBAS:
        t0 = time.time()
        try:
            r = subprocess.run(
                [sys.executable, "-X", "int_max_str_digits=0", "-c", PRE + cuerpo],
                capture_output=True, text=True, timeout=tmo, cwd=r"D:\cabal",
                env={"PYTHONIOENCODING": "utf-8", "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")})
            dt = time.time() - t0
            if r.returncode == 0:
                reg(et, "SOBREVIVE", f"{dt:.1f}s, out={r.stdout.strip()[:40]}")
            else:
                exc = r.stderr.strip().splitlines()[-1][:90] if r.stderr.strip() else "?"
                ok_honesto = ("Inseparables" in exc or "RecursionError" in exc
                              or "MemoryError" in exc or "ValueError" in exc
                              or "TypeError" in exc)
                reg(et, "CHOQUE" if not ok_honesto else "CHOQUE-DOC", exc)
        except subprocess.TimeoutExpired:
            reg(et, "CUELGUE", f">{tmo}s (matado)")


# ---------------- S2: protocolo de operadores ----------------

class ConRadd:
    def __radd__(self, o):
        return "radd-ajeno"

    def __rmul__(self, o):
        return "rmul-ajeno"


def s2_protocolo():
    try:
        r = PI + ConRadd()
        reg("PI + objeto con __radd__", "OK" if r == "radd-ajeno" else "BUG", f"r={r}")
    except TypeError as e:
        reg("PI + objeto con __radd__", "BUG",
            f"TypeError directo ({e}); __add__ deberia devolver NotImplemented "
            "para que Python pruebe el __radd__ ajeno")
    try:
        r = PI * ConRadd()
        reg("PI * objeto con __rmul__", "OK" if r == "rmul-ajeno" else "BUG", f"r={r}")
    except TypeError:
        reg("PI * objeto con __rmul__", "BUG",
            "TypeError directo; idem: falta NotImplemented en __mul__")
    from decimal import Decimal
    for et, fn in [("PI + Decimal('1')", lambda: PI + Decimal("1")),
                   ("PI + None", lambda: PI + None),
                   ("PI < 'x'", lambda: PI < "x"),
                   ("PI + [1]", lambda: PI + [1])]:
        try:
            fn()
            reg(et, "OK", "acepto (?)")
        except TypeError as e:
            reg(et, "CHOQUE-DOC", f"TypeError: {str(e)[:60]}")
        except Exception as e:
            reg(et, "CHOQUE", f"{type(e).__name__}: {str(e)[:60]}")
    try:
        import copy
        import pickle
        d = copy.deepcopy(PI * E + LN2)
        p = pickle.loads(pickle.dumps(raiz(R(7)) + 1))
        reg("deepcopy/pickle", "OK",
            f"deepcopy={d.decimales(6)} pickle={p.decimales(6)}")
    except Exception as e:
        reg("deepcopy/pickle", "CHOQUE", f"{type(e).__name__}: {str(e)[:70]}")


# ---------------- S3: entradas hostiles ----------------

def s3_hostiles():
    for s in ["", "   ", "abc", "0x10", "1/3", "nan", "inf", "1e6", "+5",
              "5_000", "--3", "."]:
        try:
            v = R(s)
            reg(f"R({s!r})", "OK", f"= {v._fr}")
        except (ValueError, ZeroDivisionError) as e:
            reg(f"R({s!r})", "CHOQUE-DOC", f"{type(e).__name__}")
        except Exception as e:
            reg(f"R({s!r})", "CHOQUE", f"{type(e).__name__}: {str(e)[:50]}")
    for et, fn in [
        ("aprox(2.5)", lambda: PI.aprox(2.5)),
        ("aprox('8')", lambda: R(Fraction(1, 3)).aprox("8")),
        ("decimales(2.5)", lambda: PI.decimales(2.5)),
        ("decimales(True)", lambda: PI.decimales(True)),
        ("signo(tope='x') de opaco 0", lambda: zero_opaco().signo(tope="x")),
        ("intervalo(-10)", lambda: PI.intervalo(-10)),
        ("iguales_hasta(PI, -5)", lambda: E.iguales_hasta(PI, -5)),
        ("R(0) ** -1", lambda: R(0) ** -1),
        ("R(0) ** 0", lambda: R(0) ** 0),
        ("opaco0 ** -2 . aprox", lambda: (zero_opaco() ** -2).aprox(8)),
    ]:
        try:
            v = fn()
            det = v if not isinstance(v, cb.Real) else f"Real({v.aprox(8)}@8)"
            reg(et, "OK", str(det)[:60])
        except (TypeError, ValueError, ZeroDivisionError, Inseparables, AttributeError) as e:
            reg(et, "CHOQUE-DOC", f"{type(e).__name__}: {str(e)[:55]}")
        except Exception as e:
            reg(et, "CHOQUE", f"{type(e).__name__}: {str(e)[:55]}")
    # TOPE roto
    viejo = cb.TOPE
    try:
        cb.TOPE = 0
        try:
            zero_opaco().signo()
            reg("TOPE=0", "BUG", "decidio el signo de un cero opaco sin presupuesto")
        except Inseparables:
            reg("TOPE=0", "OK", "degrada a Inseparables")
        cb.TOPE = -7
        try:
            (PI - 3).signo()
            reg("TOPE=-7 con valor separable", "OK", "separa pese a tope absurdo")
        except Inseparables:
            reg("TOPE=-7 con valor separable", "CHOQUE-DOC",
                "Inseparables para un valor claramente separable")
    finally:
        cb.TOPE = viejo


# ---------------- S4: concurrencia (declarada no thread-safe) ----------------

def s4_hilos():
    sys.setswitchinterval(1e-6)
    rnd = random.Random(13)
    arboles = []
    for _ in range(6):
        f1 = Fraction(rnd.randint(-99, 99), rnd.randint(1, 99))
        f2 = Fraction(rnd.randint(-99, 99), rnd.randint(1, 99))
        x = (R(f1) + zero_opaco()) * (R(f2) + zero_opaco())
        x = x * x + x - 7
        f = f1 * f2
        arboles.append((f * f + f - 7, x))
    violaciones, errores = [], []

    def trabajador(sem):
        r = random.Random(sem)
        for _ in range(1500):
            f, x = arboles[r.randrange(len(arboles))]
            p = r.randint(16, 2500)
            try:
                m = x.aprox(p)
            except Exception as e:           # cualquier explosion interna cuenta
                errores.append(f"{type(e).__name__}: {e}")
                return
            if abs(Fraction(m) - f * Fraction(2) ** p) > 1:
                violaciones.append((sem, p))

    hilos = [threading.Thread(target=trabajador, args=(i,)) for i in range(4)]
    t0 = time.time()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    dt = time.time() - t0
    sys.setswitchinterval(0.005)
    if violaciones or errores:
        reg("4 hilos x 1500 aprox en DAG compartido", "CHOQUE-DOC",
            f"{len(violaciones)} contratos rotos, {len(errores)} excepciones "
            f"({(errores or ['contrato'])[0][:60]}) en {dt:.1f}s -- la lib se declara "
            "no thread-safe: confirmado empiricamente")
    else:
        reg("4 hilos x 1500 aprox en DAG compartido", "SOBREVIVE",
            f"sin corrupcion observada en {dt:.1f}s (no es garantia)")


# ---------------- S5: blast trascendente espejado en mpmath ----------------

def _gen(rnd, d):
    """(eval_mp() -> mpf, Real) espejos exactos."""
    if d == 0:
        f = Fraction(rnd.randint(-50, 50), rnd.randint(1, 50))
        return (lambda: mpf(f.numerator) / f.denominator), R(f)
    op = rnd.choice("+-*dsceaqlt")
    g1, r1 = _gen(rnd, d - 1)
    if op in "+-*d":
        g2, r2 = _gen(rnd, d - 1)
        if op == "+":
            return (lambda: g1() + g2()), r1 + r2
        if op == "-":
            return (lambda: g1() - g2()), r1 - r2
        if op == "*":
            return (lambda: g1() * g2()), r1 * r2
        return (lambda: g1() / (g2() ** 2 + 1)), r1 / (r2 * r2 + 1)
    if op == "s":
        return (lambda: mpmath.sin(g1())), sen(r1)
    if op == "c":
        return (lambda: mpmath.cos(g1())), cos(r1)
    if op == "e":   # exp acotado: exp(3u/(1+|u|))
        return (lambda: mpmath.exp(3 * g1() / (1 + abs(g1())))), \
            exp(r1 * 3 * (1 / (1 + abs(r1))))
    if op == "a":
        return (lambda: mpmath.atan(g1())), atan(r1)
    if op == "q":
        return (lambda: mpmath.sqrt(abs(g1()))), raiz(abs(r1))
    if op == "l":
        return (lambda: mpmath.log(1 + abs(g1()))), ln(1 + abs(r1))
    return (lambda: mpmath.tan(g1())), tan(r1)


def s5_blast():
    rnd = random.Random(20260612)
    n_arboles, fallos, saltados = 250, 0, 0
    t0 = time.time()
    for i in range(n_arboles):
        g, x = _gen(rnd, 3 + (i % 2))
        for p in (0, 64, 300):
            try:
                m = x.aprox(p)
            except Inseparables:
                saltados += 1          # tan en un polo / division ~0: honesto
                break
            except (ValueError, ZeroDivisionError):
                saltados += 1          # dominio certificado
                break
            with mpmath.workprec(p + 700):
                err = abs(mpf(m) - g() * mpf(2) ** p)
                if err > 1 + mpf(2) ** -30:
                    fallos += 1
                    reg(f"blast arbol {i} p={p}", "BUG",
                        f"contrato roto: err={mpmath.nstr(err, 6)}")
    dt = time.time() - t0
    if not fallos:
        reg(f"blast {n_arboles} arboles trascendentes x3 precisiones", "SOBREVIVE",
            f"0 contratos rotos, {saltados} honestos/dominio, {dt:.0f}s")
    # torre de tan: caos iterado
    x, vx = R(1), None
    for _ in range(15):
        x = tan(x)
    try:
        m = x.aprox(80)
        with mpmath.workprec(3000):
            v = mpf(1)
            for _ in range(15):
                v = mpmath.tan(v)
            err = abs(mpf(m) - v * mpf(2) ** 80)
        reg("tan(tan(...tan(1)...)) x15 a 80 bits",
            "SOBREVIVE" if err <= 1.001 else "BUG", f"err={mpmath.nstr(err, 5)}")
    except Inseparables:
        reg("tan iterado x15", "CHOQUE-DOC", "Inseparables (iterada cerca de polo)")
    # contraste honesto: ln de racional diminuto SI, de opaco diminuto NO
    try:
        v = ln(R(10) ** -30000).decimales(3)
        reg("ln(10^-30000) racional", "SOBREVIVE", f"= {v}")
    except Exception as e:
        reg("ln(10^-30000) racional", "CHOQUE", type(e).__name__)
    m = ln(exp(R(-3000)) * 1).aprox(8)       # *1 lo vuelve compuesto-opaco
    reg("ln(exp(-3000)) opaco, valor", "SOBREVIVE" if abs(m + 3000 * 256) <= 2 else "BUG",
        f"m={m} (esperado ~{-3000*256})")
    viejo = cb.TOPE
    cb.TOPE = 4096
    try:
        ln(exp(R(-50000)) * 1).aprox(8)      # e^-50000 ~ 2^-72135 < 2^-4096
        reg("ln(exp(-50000)) opaco, TOPE=4096", "BUG", "decidio sin presupuesto")
    except Inseparables:
        reg("ln(exp(-50000)) opaco, TOPE=4096", "CHOQUE-DOC", "Inseparables (honesto)")
    finally:
        cb.TOPE = viejo
    _chk_grande()


def _chk_grande():
    with mpmath.workprec(2000):
        m = sen(R(10 ** 300)).aprox(200)
        v = mpmath.sin(mpf(10) ** 300)
        err = abs(mpf(m) - v * mpf(2) ** 200)
    reg("sen(10^300) a 200 bits", "SOBREVIVE" if err <= 1.001 else "BUG",
        f"err={mpmath.nstr(err, 5)}")


# ---------------- S6: escala ----------------

def s6_escala():
    sys.set_int_max_str_digits(0)
    filas = []
    for n in (10_000, 20_000, 40_000):
        t0 = time.time()
        PI.decimales(n, tope=10 ** 9)
        filas.append((f"pi {n} dec", time.time() - t0))
    for n in (10_000, 20_000):
        t0 = time.time()
        E.decimales(n, tope=10 ** 9)
        filas.append((f"e {n} dec", time.time() - t0))
    for n in (100_000, 1_000_000):
        t0 = time.time()
        raiz(2).decimales(n, tope=10 ** 9)
        filas.append((f"sqrt2 {n} dec", time.time() - t0))
    t0 = time.time()
    exp(PI).decimales(10_000, tope=10 ** 9)
    filas.append(("exp(pi) 10000 dec", time.time() - t0))
    t0 = time.time()
    v = (R(2) ** 1_000_000).decimales(0)
    filas.append((f"2**10^6 entero ({len(v)} digitos)", time.time() - t0))
    t0 = time.time()
    m = R(Fraction(1, 3)).aprox(-10 ** 7)
    filas.append((f"aprox(-10^7) racional (m={m})", time.time() - t0))
    for et, dt in filas:
        print(f"    [escala] {et}: {dt:.2f}s")
    reg("escala", "MEDIDO", "; ".join(f"{a}={b:.2f}s" for a, b in filas))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for s in (s1_bombas, s2_protocolo, s3_hostiles, s4_hilos, s5_blast, s6_escala):
        print(s.__name__)
        t0 = time.time()
        s()
        print(f"  ({time.time() - t0:.1f}s)")
    print(f"\nresumen: {len(RES)} casos, {len(BUGS)} BUGs")
    for b in BUGS:
        print(f"  BUG: {b}")
