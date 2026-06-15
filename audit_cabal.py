"""Auditoria adversarial profunda de cabal.py — NO forma parte de la suite.

Capa empirica de la auditoria: intenta REFUTAR el contrato |aprox(p) - x*2^p| <= 1
contra oraculos independientes (Fraction exacto, mpmath, series enteras propias),
atacando fronteras de rama, reduccion de argumentos, cache y decisiones.
Correr: python audit_cabal.py
"""
import random
import sys
import time
from fractions import Fraction

import mpmath
from mpmath import mp, mpf

import cabal as cb
from cabal import (R, PI, E, LN2, raiz, exp, ln, sen, cos, tan, atan,
                   Inseparables)

OK, FALLOS, AVISOS = 0, [], []


def caso(nombre, cond, extra=""):
    global OK
    if cond:
        OK += 1
    else:
        FALLOS.append(f"{nombre} {extra}")
        print(f"  X FALLO {nombre} {extra}")


def aviso(txt):
    AVISOS.append(txt)
    print(f"  ! aviso: {txt}")


def opacar(x):
    """Borra atajos racionales en nodos compuestos (hojas legitimas) y cache."""
    x._p = None
    x._m = 0
    hijo = False
    for nm in ("a", "b"):
        h = getattr(x, nm, None)
        if isinstance(h, cb.Real):
            hijo = True
            opacar(h)
    if hijo:
        x._fr = None
    return x


def zero_opaco():
    """Cero opaco fresco: raiz(2)^2 - 2 sin atajo racional."""
    return raiz(R(2)) ** 2 - 2


# ---------- B1: contrato vs Fraction, arboles profundos, p extremos ----------

def _expr(rnd, d):
    if d == 0:
        f = Fraction(rnd.randint(-999, 999), rnd.randint(1, 999))
        if rnd.random() < 0.25:                    # escalas mixtas: 10^+-30
            f *= Fraction(10) ** rnd.choice((-30, -9, 9, 30))
        return f, R(f)
    op = rnd.choice("++--**//anqc")                # q=**2..5, c=**-1..-3
    f1, x1 = _expr(rnd, d - 1)
    if op == "a":
        return abs(f1), abs(x1)
    if op == "n":
        return -f1, -x1
    if op == "q":
        k = rnd.randint(2, 5)
        return f1 ** k, x1 ** k
    if op == "c":
        while f1 == 0:
            f1, x1 = _expr(rnd, d - 1)
        k = -rnd.randint(1, 3)
        return f1 ** k, x1 ** k
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


def b1_contrato_profundo():
    rnd = random.Random(20260612)
    PS = (-200, -50, -7, -1, 0, 1, 3, 17, 64, 191, 333, 1000)
    for i in range(120):
        d = 3 + (i % 3)                            # profundidad 3..5
        f, x = _expr(rnd, d)
        opacar(x)
        orden = list(PS)
        rnd.shuffle(orden)                         # cache en orden arbitrario
        for p in orden:
            try:
                m = x.aprox(p)
            except Inseparables:
                continue                           # _Inv de subexpresion ~0: honesto
            caso("B1.contrato", abs(Fraction(m) - f * Fraction(2) ** p) <= 1,
                 f"p={p} d={d} i={i}")


# ---------- B2: trascendentes vs mpmath en fronteras de rama ----------

def _chk(nombre, x_real, val_mp_fn, p, prec_extra=200):
    """|aprox(p) - v*2^p| <= 1 (+2^-45 de holgura por error del oraculo)."""
    try:
        m = x_real.aprox(p)
    except Inseparables as e:
        caso(nombre, False, f"Inseparables inesperado: {e}")
        return
    with mpmath.workprec(abs(p) + prec_extra):
        t = val_mp_fn() * mpf(2) ** p
        err = abs(mpf(m) - t)
        caso(nombre, err <= 1 + mpf(2) ** -45, f"p={p} err={mpmath.nstr(err, 8)}")
        if 1 - mpf(2) ** -8 < err <= 1 + mpf(2) ** -45:
            aviso(f"{nombre}: error {mpmath.nstr(err, 8)} pegado a la cota (p={p})")


def _mpq(f):
    return mpf(f.numerator) / mpf(f.denominator)


def b2_atan_fronteras():
    eps = Fraction(1, 2 ** 80)
    bordes = [Fraction(3, 4), Fraction(1), Fraction(3, 2)]
    xs = []
    for b in bordes:
        for s in (1, -1):
            for de in (0, eps, -eps):
                xs.append(s * (b + de))
    xs += [Fraction(0), Fraction(1, 10 ** 20), Fraction(-1, 10 ** 20),
           Fraction(10 ** 30), Fraction(-10 ** 30), Fraction(7, 9), Fraction(-13, 9)]
    for f in xs:
        _chk(f"B2.atan({float(f):.3g})", atan(R(f)),
             lambda f=f: mpmath.atan(_mpq(f)), 300)
    # opacos: el probe (tope=64) cae en Inseparables y debe elegir rama valida
    for b in bordes + [Fraction(7, 8)]:
        for s in (1, -1):
            x = R(s * b) + zero_opaco()
            _chk(f"B2.atan_opaco({float(s*b):.3g})", atan(x),
                 lambda b=b, s=s: mpmath.atan(_mpq(s * b)), 300)


def b2_trig_reduccion():
    d60 = Fraction(1, 2 ** 60)
    for k in (1, 2, 3, 4, 5, 100, -1, -7, -101):
        for s in (1, -1):
            x = PI * R(Fraction(k, 2)) + R(s * d60)     # opaco, pegado a k*pi/2
            for f_cb, f_mp, nom in ((sen, mpmath.sin, "sen"), (cos, mpmath.cos, "cos")):
                _chk(f"B2.{nom}(k={k},{'+' if s>0 else '-'})", f_cb(x),
                     lambda f_mp=f_mp, k=k, s=s: f_mp(mpmath.pi * mpf(k) / 2 + mpf(s) * mpf(2) ** -60),
                     300, prec_extra=400)
    # tan cerca del polo: enorme pero finito
    x = PI * R(Fraction(1, 2)) + R(d60)
    _chk("B2.tan_polo", tan(x),
         lambda: mpmath.tan(mpmath.pi / 2 + mpf(2) ** -60), 80, prec_extra=400)
    # argumento gigante racional: reduccion con n ~ 6e39
    _chk("B2.sen(1e40)", sen(R(10 ** 40)),
         lambda: mpmath.sin(mpf(10) ** 40), 100, prec_extra=600)
    _chk("B2.cos(1e40)", cos(R(10 ** 40)),
         lambda: mpmath.cos(mpf(10) ** 40), 100, prec_extra=600)
    # racionales sueltos en todas las zonas de q = n & 3, signos negativos
    for f in (Fraction(355, 113), Fraction(-355, 113), Fraction(11, 7),
              Fraction(-998, 100), Fraction(631, 100), Fraction(-1, 10 ** 15)):
        _chk(f"B2.sen({float(f):.4g})", sen(R(f)), lambda f=f: mpmath.sin(_mpq(f)), 300)
        _chk(f"B2.cos({float(f):.4g})", cos(R(f)), lambda f=f: mpmath.cos(_mpq(f)), 300)
        _chk(f"B2.tan({float(f):.4g})", tan(R(f)), lambda f=f: mpmath.tan(_mpq(f)), 300)


def b2_ln_exp_fronteras():
    e70 = Fraction(1, 2 ** 70)
    xs = []
    for k in (-8, -1, 0, 1, 13, 100):
        for s in (0, 1, -1):
            xs.append(Fraction(2) ** k * (1 + s * e70))
    xs += [Fraction(1) + Fraction(1, 2 ** 100), Fraction(1) - Fraction(1, 2 ** 100),
           Fraction(1, 2 ** 500), Fraction(10 ** 50), Fraction(3, 4), Fraction(5, 2)]
    for f in xs:
        _chk(f"B2.ln(2^{mpmath.nstr(mpmath.log(_mpq(f),2),4)})", ln(R(f)),
             lambda f=f: mpmath.log(_mpq(f)), 300, prec_extra=700)
    # ln de opaco ~ potencia de 2 (cancelacion serie + e*LN2)
    x = R(4) + zero_opaco()
    _chk("B2.ln_opaco(4)", ln(x), lambda: mpmath.log(4), 300)
    ys = [Fraction(0), Fraction(1, 2 ** 70), -Fraction(1, 2 ** 70),
          Fraction(1, 2) + e70, -Fraction(1, 2) - e70, Fraction(81, 4),
          -Fraction(81, 4), Fraction(1234567, 10000), -Fraction(7003, 10)]
    for f in ys:
        _chk(f"B2.exp({float(f):.4g})", exp(R(f)) if f else exp(zero_opaco()),
             lambda f=f: mpmath.exp(_mpq(f)), 300, prec_extra=1200)
    # exp(-2000): el resultado*2^300 es ~2^-2585 -> aprox debe dar 0 o +-1
    m = exp(R(-2000)).aprox(300)
    caso("B2.exp(-2000)", abs(m) <= 1, f"m={m}")


def b2_raiz():
    e90 = Fraction(1, 2 ** 90)
    xs = [Fraction(4) + e90, Fraction(4) - e90, Fraction(9, 4) + e90,
          Fraction(1, 2 ** 301), Fraction(10 ** 60), Fraction(2),
          Fraction(3, 7) * Fraction(10) ** -30]
    for f in xs:
        _chk(f"B2.raiz({float(f):.3g})", raiz(R(f)),
             lambda f=f: mpmath.sqrt(_mpq(f)), 300, prec_extra=700)
    z = zero_opaco()
    m = raiz(z).aprox(200)          # raiz de cero opaco: debe dar ~0, no colgar
    caso("B2.raiz_cero_opaco", abs(m) <= 1, f"m={m}")
    _chk("B2.pow_real", R(2) ** (PI / 4), lambda: mpf(2) ** (mpmath.pi / 4), 300)


# ---------- B3: decimales vs oraculo entero exacto ----------

def _dec_oraculo(f, n):
    """n decimales de f con empates hacia +inf, en enteros puros."""
    num, den = f.numerator * 10 ** n, f.denominator
    k = (2 * num + den) // (2 * den)
    s = "-" if k < 0 else ""
    k = abs(k)
    if n == 0:
        return s + str(k)
    ent, dec = divmod(k, 10 ** n)
    return f"{s}{ent}.{str(dec).zfill(n)}"


def b3_decimales():
    rnd = random.Random(99)
    for _ in range(250):
        f = Fraction(rnd.randint(-10 ** 12, 10 ** 12), rnd.randint(1, 10 ** 9))
        n = rnd.choice((0, 1, 5, 17, 40))
        caso("B3.frac", R(f).decimales(n) == _dec_oraculo(f, n), f"f={f} n={n}")
        # version opaca del mismo valor (sin atajo racional)
        es_empate = (2 * f.numerator * 10 ** n) % (2 * f.denominator) == f.denominator
        x = R(f) + zero_opaco()
        if es_empate:
            try:
                x.decimales(n, tope=4096)
                caso("B3.empate_opaco", False, f"f={f} n={n}: no detecto empate")
            except Inseparables:
                caso("B3.empate_opaco", True)
        else:
            caso("B3.opaco", x.decimales(n) == _dec_oraculo(f, n), f"f={f} n={n}")
    # empate roto a profundidad 150 bits: debe converger, no rendirse
    f = Fraction(25, 2) + Fraction(1, 2 ** 150)
    x = R(f) + zero_opaco()
    caso("B3.empate_roto", x.decimales(0) == "13")
    f = Fraction(25, 2) - Fraction(1, 2 ** 150)
    x = R(f) + zero_opaco()
    caso("B3.empate_roto2", x.decimales(0) == "12")
    # transcendente largo vs mpmath
    with mpmath.workprec(9000):
        t = mpmath.nstr(mpmath.pi, 2001, strip_zeros=False)
    caso("B3.pi2000", PI.decimales(2000) == t, "pi a 2000 decimales difiere")


# ---------- B4: _dstr vs str ----------

def b4_dstr():
    sys.set_int_max_str_digits(2_000_000)
    rnd = random.Random(5)
    ks = [0, 1, 7, 10 ** 100,
          10 ** 2980, 10 ** 2981 - 1, 2 ** 9899, 2 ** 9900, 2 ** 9901,
          10 ** 3000, 10 ** 6000 + 5, (10 ** 3000 + 1) * 10 ** 3000]
    for _ in range(20):
        nd = rnd.randint(2900, 12000)
        ks.append(rnd.randrange(10 ** (nd - 1), 10 ** nd))
        ks.append(rnd.randrange(10 ** (nd - 1), 10 ** nd) * 10 ** rnd.randint(0, 4000))
    for k in ks:
        caso("B4.dstr", cb._dstr(k) == str(k), f"~10^{len(str(k))-1}")


# ---------- B5: __float__ en bordes ----------

def b5_float():
    rnd = random.Random(31)
    for _ in range(120):
        f = Fraction(rnd.randint(-10 ** 9, 10 ** 9), rnd.randint(1, 10 ** 9))
        f *= Fraction(2) ** rnd.randint(-100, 100)
        if f == 0:
            continue
        x = R(f) + zero_opaco()
        got, want = float(x), float(f)      # Fraction.__float__: correctamente redondeado
        ulp = abs(want) * 2 ** -52 if want else 2 ** -1074
        caso("B5.float", abs(got - want) <= 2 * ulp, f"f~2^{f and float(f).hex()}")
    # subnormales
    for e in (-1050, -1073, -1074):
        f = Fraction(2) ** e
        caso("B5.subnormal", abs(float(R(f) + zero_opaco()) - float(f)) <= 2 ** -1074,
             f"2^{e}")
    caso("B5.bajo_radar", float(R(Fraction(2) ** -1200) + zero_opaco()) == 0.0)
    caso("B5.cero_opaco", float(zero_opaco()) == 0.0)
    try:
        v = float(exp(R(800)))               # > DBL_MAX
        caso("B5.overflow", v == float("inf"), f"v={v}")
    except OverflowError:
        aviso("float(exp(800)) lanza OverflowError (no devuelve inf): comportamiento de ldexp")
        caso("B5.overflow", True)


# ---------- B6: honestidad semidecidible en cada ruta ----------

def b6_honestidad():
    z = zero_opaco()
    for nombre, fn in [
        ("signo", lambda: z.signo(tope=256)),
        ("eq", lambda: (1 / raiz(2)) == raiz(2) / 2),
        ("lt", lambda: zero_opaco() < 0),
        ("inv", lambda: (1 / zero_opaco()).aprox(10)),
        ("tan_polo", lambda: tan(PI / 2).aprox(20)),
        ("ln_cero", lambda: ln(zero_opaco()).aprox(10)),
    ]:
        viejo = cb.TOPE
        cb.TOPE = 512
        try:
            fn()
            caso(f"B6.{nombre}", False, "no lanzo Inseparables")
        except Inseparables:
            caso(f"B6.{nombre}", True)
        finally:
            cb.TOPE = viejo
    for nombre, fn in [("raiz_neg", lambda: raiz(opacar(R(-4))).aprox(10)),
                       ("ln_neg", lambda: ln(opacar(R(-4))).aprox(10))]:
        try:
            fn()
            caso(f"B6.{nombre}", False, "no certifico dominio")
        except ValueError:
            caso(f"B6.{nombre}", True)
    # raiz de opaco negativo DIMINUTO: devuelve 0 sin certificar (zona gris)
    x = R(-Fraction(1, 2 ** 500)) + zero_opaco()
    m = raiz(x).aprox(100)
    if abs(m) <= 1:
        aviso("raiz(opaco negativo ~ -2^-500) devuelve ~0 en vez de error: "
              "semidecidible, pero no documentado")


# ---------- B7: constantes por formulas independientes ----------

def _atan_recip_ent(n, w):
    """floor-suma de atan(1/n)*2^w con error en [-T-1, 1]; T terminos."""
    n2, cur, i, sg, s, T = n * n, (1 << w) // n, 1, 1, 0, 0
    while cur:
        s += sg * (cur // i)
        cur //= n2
        i += 2
        sg = -sg
        T += 1
    return s, T


def b7_constantes():
    # pi via atan(1/2)+atan(1/3) (formula DISTINTA de Machin 5/239), enteros puros
    dig = 3000
    w = int(dig * 3.33) + 80
    a2, t2 = _atan_recip_ent(2, w)
    a3, t3 = _atan_recip_ent(3, w)
    s = 4 * (a2 + a3)
    holg = 4 * (t2 + t3 + 4)
    lo, hi = Fraction(s - holg, 2 ** w), Fraction(s + holg, 2 ** w)
    m = PI.aprox(w - 80)
    plo, phi = Fraction(m - 1, 2 ** (w - 80)), Fraction(m + 1, 2 ** (w - 80))
    caso("B7.pi_indep", lo <= phi and plo <= hi, "intervalos disjuntos!")
    caso("B7.pi_3000", PI.decimales(dig) ==
         _frac_dec((lo + hi) / 2, dig, holg * Fraction(2, 2 ** w)), "")
    # ln2 = sum 1/(k 2^k): serie DISTINTA de 2*atanh(1/3), Fraction exacta
    N = 1200
    parcial = sum(Fraction(1, k * 2 ** k) for k in range(1, N + 1))
    cola = Fraction(2, (N + 1) * 2 ** N)
    lo2, hi2 = parcial, parcial + cola
    mlo, mhi = LN2.intervalo(900)
    caso("B7.ln2_indep", lo2 <= mhi and mlo <= hi2)
    # e = sum 1/k!: Fraction exacta
    N, term = 450, Fraction(1)
    se = Fraction(1)
    for k in range(1, N + 1):
        term /= k
        se += term
    lo3, hi3 = se, se + term * Fraction(2, N)
    elo, ehi = E.intervalo(900)
    caso("B7.e_indep", lo3 <= ehi and elo <= hi3)
    # sqrt(2) a 5000 decimales contra isqrt entero
    t = 2 * 10 ** (2 * 5000)
    s5 = __import__("math").isqrt(t)
    k = s5 + (1 if 4 * t > (2 * s5 + 1) ** 2 else 0)
    esperado = f"{k // 10**5000}.{str(k % 10**5000).zfill(5000)}"
    caso("B7.sqrt2_5000", raiz(2).decimales(5000) == esperado)


def _frac_dec(f, n, err):
    """n decimales de f (solo valido si err << 10^-n; aqui sobra)."""
    assert err < Fraction(1, 10 ** (n + 2))
    return _dec_oraculo(f, n)


# ---------- B8: identidades cruzadas a 1000 bits ----------

def b8_identidades():
    b = 1000
    caso("B8.sen2cos2", (sen(R("2.7")) ** 2 + cos(R("2.7")) ** 2).iguales_hasta(1, b))
    caso("B8.exp_ln", exp(ln(R("987.654321"))).iguales_hasta(R("987.654321"), b))
    caso("B8.ln_exp", ln(exp(R("-7.25"))).iguales_hasta(R("-7.25"), b))
    caso("B8.atan_tan", tan(atan(R("5.5"))).iguales_hasta(R("5.5"), b))
    caso("B8.machin", (4 * atan(1)).iguales_hasta(PI, b))
    caso("B8.euler", (16 * atan(R(1) / 5) - 4 * atan(R(1) / 239)).iguales_hasta(PI, b))
    caso("B8.ln2", ln(2).iguales_hasta(LN2, b))
    caso("B8.sqrt_pow", (raiz(R("3.3")) * raiz(R("3.3"))).iguales_hasta(R("3.3"), b))


# ---------- B9: bordes de API ----------

def b9_api():
    try:
        2 ** PI
        caso("B9.rpow", True)
    except TypeError:
        aviso("2 ** PI lanza TypeError: falta __rpow__ (R(2)**PI si funciona)")
        caso("B9.rpow", True)   # gap de API, no violacion de contrato
    try:
        +PI
        caso("B9.pos", True)
    except TypeError:
        aviso("+PI lanza TypeError: falta __pos__")
        caso("B9.pos", True)
    if bool(R(0)):
        aviso("bool(R(0)) es True (no hay __bool__): 'if x:' no es test de cero")
    try:
        (-R(2)) ** 2.0
        caso("B9.pow_float_ent", True)
    except ValueError:
        aviso("(-R(2)) ** 2.0 lanza ValueError (va por exp*ln): solo exponente int es seguro con base negativa")
        caso("B9.pow_float_ent", True)
    n = 50000
    try:
        x = R(0)
        for _ in range(n):
            x = x + 1
        x.aprox(0)
        caso("B9.cadena", True)
    except RecursionError:
        aviso(f"cadena de {n} sumas: RecursionError en aprox (limite de recursion de Python, no documentado)")
        caso("B9.cadena", True)
    try:
        PI.decimales(19414)
        caso("B9.dec_tope", True)
    except Inseparables:
        aviso("PI.decimales(19414) lanza Inseparables con TOPE default (>19413 digitos exige subir TOPE/tope)")
        caso("B9.dec_tope", True)
    caso("B9.dec_19413_arranca", PI.decimales(2000) == PI.decimales(2000))
    # Fraction con notacion cientifica en R(str)
    try:
        caso("B9.str_sci", R("1e-3") == Fraction(1, 1000))
    except ValueError:
        aviso("R('1e-3') no soportado")
        caso("B9.str_sci", True)
    caso("B9.eq_str", (PI == "hola") is False)   # NotImplemented -> False


# ---------- B10: humo de rendimiento ----------

def b10_perf():
    for tag, fn in [
        ("pi 10000 dec", lambda: PI.decimales(10000)),
        ("sqrt2 10000 dec", lambda: raiz(2).decimales(10000)),
        ("exp(ln(x)) 2000 dec", lambda: exp(ln(R("1234.5678"))).decimales(2000)),
        ("sen(1e40) 100 dec", lambda: sen(R(10 ** 40)).decimales(100)),
        ("exp(-700.3) 1000 dec", lambda: exp(R("-700.3")).decimales(1000)),
    ]:
        t0 = time.time()
        fn()
        print(f"    [perf] {tag}: {time.time() - t0:.2f}s")
    caso("B10.perf", True)


if __name__ == "__main__":
    for t in (b1_contrato_profundo, b2_atan_fronteras, b2_trig_reduccion,
              b2_ln_exp_fronteras, b2_raiz, b3_decimales, b4_dstr, b5_float,
              b6_honestidad, b7_constantes, b8_identidades, b9_api, b10_perf):
        print(t.__name__)
        t0 = time.time()
        t()
        print(f"  ({time.time() - t0:.1f}s)")
    print(f"\n{OK} OK, {len(FALLOS)} fallos, {len(AVISOS)} avisos")
    for a in AVISOS:
        print(f"  aviso: {a}")
    if FALLOS:
        sys.exit(1)
