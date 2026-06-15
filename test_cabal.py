"""Anclas de prueba de cabal. Correr: python3 test_cabal.py

A1 es el experimento que mata la idea: el contrato |aprox(p) - x·2^p| <= 1
se verifica contra Fraction (oráculo exacto independiente) en árboles aleatorios.
"""
import math
import random
import sys
import time
from fractions import Fraction

import cabal as cb
from cabal import R, PI, E, LN2, raiz, exp, ln, sen, cos, tan, atan, Inseparables

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows: consola cp1252 vs π/√

OK, FALLOS = 0, []


def caso(nombre, cond, extra=""):
    global OK
    if cond:
        OK += 1
    else:
        FALLOS.append(f"{nombre} {extra}")
        print(f"  ✗ {nombre} {extra}")


def _op(x):
    """Opaca un árbol: borra atajos racionales en nodos compuestos (las hojas son legítimas)."""
    x._p = None
    x._m = 0
    hijo = False
    for nm in ("a", "b"):
        h = getattr(x, nm, None)
        if isinstance(h, cb.Real):
            hijo = True
            _op(h)
    if hijo:
        x._fr = None
    return x


def _expr(rnd, d):
    """(Fraction exacta, Real) con la misma estructura."""
    if d == 0:
        f = Fraction(rnd.randint(-99, 99), rnd.randint(1, 99))
        return f, R(f)
    op = rnd.choice("+-*/an")
    f1, x1 = _expr(rnd, d - 1)
    if op == "a":
        return abs(f1), abs(x1)
    if op == "n":
        return -f1, -x1
    f2, x2 = _expr(rnd, d - 1)
    if op == "+":
        return f1 + f2, x1 + x2
    if op == "-":
        return f1 - f2, x1 - x2
    if op == "*":
        return f1 * f2, x1 * x2
    while f2 == 0:
        f2, x2 = _expr(rnd, d - 1)
    return f1 / f2, x1 / x2


# ---------- A1: contrato <=1 ulp contra oráculo Fraction ----------

def test_contrato():
    rnd = random.Random(7)
    for _ in range(60):
        f, x = _expr(rnd, 3)
        _op(x)
        for p in (-7, 0, 3, 17, 64, 191):
            m = x.aprox(p)
            caso("A1.contrato", abs(Fraction(m) - f * Fraction(2) ** p) <= 1, f"f={f} p={p}")
        # camino de caché (descendente reutiliza _m desplazado)
        for p in (191, 64, 17, 0, -7):
            m = x.aprox(p)
            caso("A1.cache", abs(Fraction(m) - f * Fraction(2) ** p) <= 1, f"f={f} p={p}")


# ---------- A2: raíz (oráculo indirecto y exacto) ----------

def test_raiz():
    rnd = random.Random(11)
    for _ in range(15):
        f = abs(Fraction(rnd.randint(1, 999), rnd.randint(1, 99)))
        d = raiz(_op(R(f))) ** 2 - R(f)
        caso("A2.sqrt²=x", abs(d.aprox(220)) <= 4, f"f={f}")
    caso("A2.exacta", raiz(R(Fraction(9, 4))) == Fraction(3, 2))
    # oráculo independiente para dígitos de sqrt(2): isqrt entero
    t = 2 * 10 ** 80
    s = isqrt_(t)
    k = s + (1 if 4 * t > (2 * s + 1) ** 2 else 0)   # round(sqrt(2)·10^40)
    esperado = f"{k // 10**40}.{k % 10**40:040d}"
    caso("A2.digitos", raiz(2).decimales(40) == esperado, raiz(2).decimales(40))


def isqrt_(n):
    from math import isqrt
    return isqrt(n)


# ---------- A3: constantes (prefijos sobre salida más larga: inmune al redondeo) ----------

def test_constantes():
    caso("A3.pi", PI.decimales(50).startswith("3.141592653589793238462643383279502884197"))
    caso("A3.e", E.decimales(50).startswith("2.71828182845904523536028747135266249775"))
    caso("A3.ln2", LN2.decimales(45).startswith("0.6931471805599453094172321214581765680"))
    caso("A3.float_pi", abs(float(PI) - math.pi) < 1e-15)
    caso("A3.float_e", abs(float(E) - math.e) < 1e-15)


# ---------- A4: identidades a 300 bits (rutas independientes) ----------

def test_identidades():
    b = 300
    for x in (R("1.7"), -R(3) / 7, R(10)):
        caso("A4.sen²+cos²", (sen(x) ** 2 + cos(x) ** 2).iguales_hasta(1, b))
    a, c = R("0.3"), R("-2.5")
    caso("A4.exp_suma", exp(a + c).iguales_hasta(exp(a) * exp(c), b))
    caso("A4.ln_prod", ln(R("3.7") * 11).iguales_hasta(ln(R("3.7")) + ln(11), b))
    caso("A4.exp_ln", exp(ln(R("123.456"))).iguales_hasta(R("123.456"), b))
    caso("A4.ln_exp", ln(exp(-R(2) / 3)).iguales_hasta(-R(2) / 3, b))
    caso("A4.tan_pi4", tan(PI / 4).iguales_hasta(1, b))
    caso("A4.sen_pi6", sen(PI / 6).iguales_hasta(R(Fraction(1, 2)), b))
    caso("A4.cos_pi3", cos(PI / 3).iguales_hasta(R(Fraction(1, 2)), b))
    caso("A4.sen_pi", sen(PI).iguales_hasta(0, b))
    caso("A4.atan_mitad", (4 * atan(1)).iguales_hasta(PI, b))          # rama mitad vs Machin
    caso("A4.atan_recip", (atan(5) + atan(R(1) / 5)).iguales_hasta(PI / 2, b))
    caso("A4.machin_gral", (16 * atan(R(1) / 5) - 4 * atan(R(1) / 239)).iguales_hasta(PI, b))
    caso("A4.raices", (raiz(2) * raiz(8)).iguales_hasta(4, b))
    caso("A4.inv_inv", (1 / (1 / R("3.7"))).iguales_hasta(R("3.7"), b))
    caso("A4.pow_real", (R(2) ** R("0.5")).iguales_hasta(raiz(2), b))


# ---------- A5: semidecidibilidad honesta y orden ----------

def test_decision():
    z = raiz(_op(R(2))) ** 2 - 2          # cero opaco
    try:
        z.signo(tope=512)
        caso("A5.insep_signo", False)
    except Inseparables:
        caso("A5.insep_signo", True)
    caso("A5.insep_cerca", z.iguales_hasta(0, 300))
    caso("A5.orden1", PI > 3)
    caso("A5.orden2", PI < R("3.15"))
    caso("A5.orden3", E < PI)
    caso("A5.eq_exacta", R("0.1") + R("0.2") == R("0.3"))
    caso("A5.eq_frac", R(1) / 3 == Fraction(1, 3))
    viejo = cb.TOPE
    cb.TOPE = 512
    try:
        (1 / raiz(2)) == raiz(2) / 2      # iguales y opacos: debe rendirse, no mentir
        caso("A5.eq_opaca", False)
    except Inseparables:
        caso("A5.eq_opaca", True)
    finally:
        cb.TOPE = viejo


# ---------- A6: decimales correctamente redondeados ----------

def test_decimales():
    caso("A6.tercio", (R(1) / 3).decimales(10) == "0.3333333333")
    caso("A6.redondeo", (R(2) / 3).decimales(10) == "0.6666666667")
    caso("A6.negativo", (-R(2) / 3).decimales(10) == "-0.6666666667")
    caso("A6.empate+", R("12.5").decimales(0) == "13")
    caso("A6.empate-", R("-12.5").decimales(0) == "-12")   # empates hacia +inf
    caso("A6.exacto", (R("0.1") + R("0.2")).decimales(5) == "0.30000")
    caso("A6.entero", R(7).decimales(0) == "7")


# ---------- A7: contraste con math (doble precisión) ----------

def test_float():
    pares = [(sen, math.sin), (cos, math.cos), (tan, math.tan),
             (atan, math.atan), (exp, math.exp)]
    for xf in (-3.3, -1.0, -0.2, 0.4, 1.0, 2.7, 9.9):
        for f, g in pares:
            caso("A7." + g.__name__, abs(float(f(R(xf))) - g(xf)) <= 1e-12 * max(1.0, abs(g(xf))),
                 f"x={xf}")
    for xf in (0.01, 0.6, 1.0, 5.5, 123.0):
        caso("A7.log", abs(float(ln(R(xf))) - math.log(xf)) <= 1e-12 * max(1.0, abs(math.log(xf))), f"x={xf}")
        caso("A7.sqrt", abs(float(raiz(R(xf))) - math.sqrt(xf)) <= 1e-12 * math.sqrt(xf), f"x={xf}")
    caso("A7.exp20", abs(float(exp(R(20))) - math.exp(20)) <= 1e-10 * math.exp(20))
    caso("A7.expm30", abs(float(exp(R(-30))) - math.exp(-30)) <= 1e-10 * math.exp(-30))


# ---------- A8: dominios y errores ----------

def test_dominios():
    for fn, arg, exc in ((raiz, R(-4), ValueError), (ln, R(-1), ValueError),
                         (ln, R(0), ValueError)):
        try:
            fn(arg)
            caso("A8." + fn.__name__, False)
        except exc:
            caso("A8." + fn.__name__, True)
    try:
        R(1) / R(0)
        caso("A8.div0", False)
    except ZeroDivisionError:
        caso("A8.div0", True)
    try:
        ln(_op(R(-4))).aprox(10)          # negativo opaco: certificado en evaluación
        caso("A8.ln_opaco", False)
    except ValueError:
        caso("A8.ln_opaco", True)


# ---------- A9: cercos racionales certificados ----------

def test_cercos():
    lo, hi = PI.intervalo(100)
    caso("A9.sandwich", Fraction(333, 106) < lo < hi < Fraction(355, 113))
    caso("A9.ancho", hi - lo == Fraction(2, 2 ** 100))
    m2 = PI.aprox(200)   # cerco más fino debe caer dentro del grueso
    caso("A9.anidado", lo <= Fraction(m2 - 1, 2 ** 200) and Fraction(m2 + 1, 2 ** 200) <= hi)


# ---------- A11: API: pos, rpow, pow exacto, bool, ±inf/nan, presupuesto ----------

def test_api():
    caso("A11.pos", (+PI) is PI)
    caso("A11.rpow_exacto", 2 ** R(3) == 8)
    caso("A11.rpow_frac", Fraction(1, 4) ** R(Fraction(1, 2)) == Fraction(1, 2))
    caso("A11.rpow_opaco", (2 ** PI).iguales_hasta(exp(PI * LN2), 300))
    caso("A11.pow_real_exacto", R(2) ** R(10) == 1024)
    caso("A11.pow_float_ent", (-R(2)) ** 2.0 == 4)
    caso("A11.bool0", bool(R(0)) is False)
    caso("A11.bool_pi", bool(PI) is True)
    z = raiz(_op(R(2))) ** 2 - 2
    viejo = cb.TOPE
    cb.TOPE = 512
    try:
        bool(z)                            # cero opaco: debe rendirse, no decidir
        caso("A11.bool_opaco", False)
    except Inseparables:
        caso("A11.bool_opaco", True)
    finally:
        cb.TOPE = viejo
    nan, inf = float("nan"), float("inf")
    caso("A11.eq_nan", (PI == nan) is False)
    caso("A11.ne_nan", (PI != nan) is True)
    caso("A11.lt_nan", (PI < nan) is False)
    caso("A11.eq_inf", (PI == inf) is False)
    caso("A11.lt_inf", (PI < inf) is True)
    caso("A11.gt_ninf", (PI > -inf) is True)
    caso("A11.le_ninf", (PI <= -inf) is False)
    caso("A11.ge_inf", (PI >= inf) is False)
    try:
        PI.decimales(30000)                # ~101k bits > TOPE: mensaje de presupuesto
        caso("A11.presupuesto", False)
    except Inseparables as e:
        caso("A11.presupuesto", "presupuesto" in str(e), str(e))

    class _Ajeno:                          # protocolo: deferir al operador reflejado
        def __radd__(self, o):
            return "radd"

        def __rmul__(self, o):
            return "rmul"
    caso("A11.radd_ajeno", (PI + _Ajeno()) == "radd")
    caso("A11.rmul_ajeno", (PI * _Ajeno()) == "rmul")
    try:
        PI < "x"                           # == da False; < debe dar TypeError
        caso("A11.lt_str", False)
    except TypeError:
        caso("A11.lt_str", True)
    try:
        z.signo(tope=float("inf"))         # presupuesto no-int: error, no cuelgue
        caso("A11.tope_float", False)
    except TypeError:
        caso("A11.tope_float", True)


# ---------- A10: humo de rendimiento ----------

def test_humo():
    t0 = time.time()
    d = PI.decimales(1000)
    dt = time.time() - t0
    caso("A10.pi1000", d.startswith("3.14159265358979323846264338327950288419716939937510"))
    print(f"  π a 1000 decimales: {dt:.2f}s")
    t0 = time.time()
    raiz(2).decimales(2000)
    print(f"  √2 a 2000 decimales: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    for t in (test_contrato, test_raiz, test_constantes, test_identidades,
              test_decision, test_decimales, test_float, test_dominios,
              test_cercos, test_api, test_humo):
        print(t.__name__)
        t()
    print(f"\n{OK} OK, {len(FALLOS)} fallos")
    if FALLOS:
        sys.exit(1)
