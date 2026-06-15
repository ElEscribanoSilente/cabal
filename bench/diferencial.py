# -*- coding: utf-8 -*-
"""Validación diferencial de cabal contra mpmath (oráculo independiente).

Estrategia:
  1) Contrato central: |aprox(p) - x*2^p| <= 1  (verificado contra mpmath exacto).
  2) Cerco certificado: el valor verdadero (mpmath) cae dentro de intervalo(bits).
  3) Exactitud racional (sin mpmath): 0.1+0.2 == 0.3, etc.
  4) Identidades: sin^2+cos^2=1, exp(ln x)=x, raiz(x)^2=x, ...
  5) Honestidad: Inseparables cuando un opaco no se separa de 0.
  6) Manejo de errores de dominio.
  7) Conversión a float correctamente redondeada.
  8) decimales() comparado dígito a dígito con mpmath (hasta 1000 cifras de PI).

Uso:  pip install mpmath  &&  python bench/diferencial.py   (desde la raíz del repo)
"""
import sys, os, time, math
from fractions import Fraction
from decimal import Decimal, getcontext, ROUND_HALF_UP

import mpmath as mp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import cabal
from cabal import (R, PI, E, LN2, raiz, exp, ln, sen, cos, tan, atan,
                   Inseparables, TOPE)

print("cabal", cabal.__version__, "desde", cabal.__file__)
print("mpmath", mp.__version__)
print("python", sys.version.split()[0])
print("=" * 70)

mp.mp.dps = 160
getcontext().prec = 4000

P = F = 0
fails = []
def ok(name, cond, detail=""):
    global P, F
    if cond:
        P += 1
    else:
        F += 1
        fails.append((name, detail))
        print(f"  [FAIL] {name}   {detail}")

def section(t):
    print(f"\n--- {t} ---")

def ofrac(mpfn, sig):
    """Fraction de mpfn() a 'sig' cifras significativas (precisión temporal)."""
    with mp.workdps(sig + 25):
        s = mp.nstr(mpfn(), sig, strip_zeros=False)
    return Fraction(Decimal(s))

# 1) ------------------- CONTRATO CENTRAL -------------------
section("1. Contrato  |aprox(p) - x*2^p| <= 1")
def contrato(name, expr, mpfn, ps):
    for p in ps:
        m = expr.aprox(p)
        sig = int(p * 0.302) + 50
        o = ofrac(mpfn, sig)
        err = abs(Fraction(m) - o * (Fraction(2) ** p))
        ok(f"{name} p={p}", err <= Fraction(1) + Fraction(1, 10**8),
           f"err={float(err):.6f}")

contrato("PI",      PI,        lambda: mp.pi,            [0,1,8,53,120,300,1000])
contrato("E",       E,         lambda: mp.e,             [0,1,8,53,120,300,1000])
contrato("LN2",     LN2,       lambda: mp.log(2),        [0,1,53,300,1000])
contrato("exp(1)",  exp(1),    lambda: mp.e,             [0,53,300])
contrato("ln(2)",   ln(2),     lambda: mp.log(2),        [0,53,300])
contrato("raiz2",   raiz(2),   lambda: mp.sqrt(2),       [0,53,300,1000])
contrato("sen(1)",  sen(1),    lambda: mp.sin(1),        [0,53,300])
contrato("cos(1)",  cos(1),    lambda: mp.cos(1),        [0,53,300])
contrato("atan(1)", atan(1),   lambda: mp.atan(1),       [0,53,300])

# 2) ------------------- CERCO CERTIFICADO -------------------
section("2. intervalo(bits): el valor verdadero cae dentro del cerco")
def dentro(name, expr, mpfn, bits=120, sig=130):
    lo, hi = expr.intervalo(bits)
    o = ofrac(mpfn, sig)
    ok(name, lo <= o <= hi,
       f"lo={float(lo):.4e} o={float(o):.4e} hi={float(hi):.4e}")

dentro("exp(50)",     exp(50),          lambda: mp.e**50)
dentro("exp(-50)",    exp(-50),         lambda: mp.e**-50)
dentro("exp(100)",    exp(100),         lambda: mp.e**100)
dentro("ln(1e100)",   ln(R(10)**100),   lambda: mp.log(mp.mpf(10)**100))
dentro("ln(1/7)",     ln(R(1)/7),       lambda: mp.log(mp.mpf(1)/7))
dentro("sen(1000)",   sen(1000),        lambda: mp.sin(1000))
dentro("cos(1000)",   cos(1000),        lambda: mp.cos(1000))
dentro("sen(-3.5)",   sen(R('-3.5')),   lambda: mp.sin(mp.mpf('-3.5')))
dentro("cos(3.5)",    cos(R('3.5')),    lambda: mp.cos(mp.mpf('3.5')))
dentro("tan(1)",      tan(1),           lambda: mp.tan(1))
dentro("tan(1.2)",    tan(R('1.2')),    lambda: mp.tan(mp.mpf('1.2')))
dentro("atan(1)",     atan(1),          lambda: mp.atan(1))
dentro("atan(5)",     atan(5),          lambda: mp.atan(5))
dentro("atan(-0.3)",  atan(R('-0.3')),  lambda: mp.atan(mp.mpf('-0.3')))
dentro("atan(100)",   atan(100),        lambda: mp.atan(100))
dentro("raiz(2)",     raiz(2),          lambda: mp.sqrt(2))
dentro("raiz(1e-9)",  raiz(R('1e-9')),  lambda: mp.sqrt(mp.mpf('1e-9')))
dentro("2**0.5",      R(2)**0.5,        lambda: mp.sqrt(2))
dentro("3**(1/3)",    R(3)**Fraction(1,3), lambda: mp.mpf(3)**(mp.mpf(1)/3))
dentro("PI*E",        PI*E,             lambda: mp.pi*mp.e)
dentro("PI-3",        PI-3,             lambda: mp.pi-3)
dentro("4*atan(1)",   4*atan(1),        lambda: mp.pi)

# 3) ------------------- EXACTITUD RACIONAL (sin mpmath) -------------------
section("3. Exactitud racional (lo que el float NO puede)")
ok("0.1+0.2 == 0.3", R('0.1') + R('0.2') == R('0.3'))
ok("0.1+0.2 decimales", (R('0.1')+R('0.2')).decimales(25) == "0." + "3" + "0"*24)
ok("(0.1+0.2-0.3) signo 0", (R('0.1')+R('0.2')-R('0.3')).signo() == 0)
ok("1/3 a 30 dec", (R(1)/3).decimales(30) == "0." + "3"*30)
ok("2/3 a 30 dec", (R(2)/3).decimales(30) == "0." + "6"*29 + "7")  # redondeo
ok("2**100 exacto", (R(2)**100).decimales(0) == str(2**100))
ok("7**-2 == 1/49", R(7)**(-2) == Fraction(1,49))
ok("(-3)**3 == -27", R(-3)**3 == -27)
ok("frac suma exacta", R(Fraction(1,7)) + R(Fraction(1,7)) == Fraction(2,7))
ok("raiz(4)==2 exacto", raiz(4) == 2)
ok("raiz(9/4)==3/2", raiz(Fraction(9,4)) == Fraction(3,2))
ok("exp(0)==1", exp(0) == 1)
ok("ln(1)==0", ln(1) == 0)
ok("sen(0)==0", sen(0) == 0)
ok("cos(0)==1", cos(0) == 1)

# 4) ------------------- IDENTIDADES (via intervalo ~ valor) -------------------
section("4. Identidades algebraicas")
def ident(name, expr, target, bits=120):
    lo, hi = expr.intervalo(bits)
    t = Fraction(target)
    ok(name, lo <= t <= hi, f"lo={float(lo):.4e} t={float(t)} hi={float(hi):.4e}")

ident("sin^2+cos^2=1 (x=1.3)", sen(R('1.3'))**2 + cos(R('1.3'))**2, 1)
ident("sin^2+cos^2=1 (x=10)",  sen(10)**2 + cos(10)**2, 1)
ident("exp(ln 5)=5",           exp(ln(5)), 5)
ident("ln(exp 3)=3",           ln(exp(3)), 3)
ident("raiz(2)^2=2",           raiz(2)**2, 2)
ident("raiz(x)^2=x (x=123)",   raiz(123)**2, 123)
ident("exp(a+b)=exp a*exp b",  exp(R('1.5')+R('0.7')) - exp(R('1.5'))*exp(R('0.7')), 0)
ident("ln(a*b)=ln a+ln b",     ln(R(6)*R(7)) - (ln(6)+ln(7)), 0)
ident("atan(tan .7)=.7",       atan(tan(R('0.7'))), Fraction(7,10))
ident("tan=sen/cos (x=1)",     tan(1) - sen(1)/cos(1), 0)
ident("2*atan(1)... pi/2",     2*atan(1) - PI/2, 0)

# 5) ------------------- HONESTIDAD: Inseparables -------------------
section("5. Honestidad computacional (semidecidibilidad)")
d = raiz(2)*raiz(2) - 2          # exactamente 0 pero opaco
try:
    d.signo(tope=4000); ok("opaco~0 lanza Inseparables", False, "no lanzó")
except Inseparables:
    ok("opaco~0 lanza Inseparables", True)
ok("iguales_hasta es total", d.iguales_hasta(0, 256) is True)
try:
    bool(d); ok("bool(opaco~0) lanza Inseparables", False)
except Inseparables:
    ok("bool(opaco~0) lanza Inseparables", True)

# 6) ------------------- ERRORES DE DOMINIO -------------------
section("6. Manejo de errores de dominio")
def lanza(name, fn, exc):
    try:
        fn(); ok(name, False, "no lanzó")
    except exc:
        ok(name, True)
    except Exception as e:
        ok(name, False, f"lanzó {type(e).__name__}: {e}")

lanza("1/0 -> ZeroDivisionError", lambda: R(1)/R(0), ZeroDivisionError)
lanza("raiz(-1) -> ValueError",   lambda: raiz(-1), ValueError)
lanza("ln(0) -> ValueError",      lambda: ln(0), ValueError)
lanza("ln(-2) -> ValueError",     lambda: ln(-2), ValueError)
lanza("R(inf) -> ValueError",     lambda: R(float('inf')), ValueError)
lanza("R(nan) -> ValueError",     lambda: R(float('nan')), ValueError)
lanza("R([]) -> TypeError",       lambda: R([]), TypeError)

# 7) ------------------- COMPARACIONES -------------------
section("7. Comparaciones certificadas")
ok("PI > 3",            PI > 3)
ok("PI < 22/7",         PI < Fraction(22,7))
ok("PI > 311/99",       PI > Fraction(311,99))
ok("E > 2.7",           E > Fraction(27,10))
ok("E < 2.72",          E < Fraction(272,100))
ok("raiz2 < 3/2",       raiz(2) < Fraction(3,2))
ok("raiz2 > 7/5",       raiz(2) > Fraction(7,5))
ok("ln(2) en (0.69,0.70)", Fraction(69,100) < ln(2) < Fraction(70,100))
ok("-PI < -3",          -PI < -3)
ok("PI > E",            PI > E)

# 8) ------------------- FLOAT correctamente redondeado -------------------
section("8. __float__ (redondeo correcto al double más cercano)")
ok("float(PI)==math.pi",    float(PI) == math.pi)
ok("float(E)==math.e",      float(E) == math.e)
ok("float(LN2)==log(2)",    float(LN2) == math.log(2))
ok("float(raiz2)==sqrt2",   float(raiz(2)) == math.sqrt(2))
ok("float(exp1)==e",        float(exp(1)) == math.e)
ok("float(sen(1))==sin(1)", float(sen(1)) == math.sin(1))
ok("float(cos(1))==cos(1)", float(cos(1)) == math.cos(1))
ok("float(ln(10))==log10base", float(ln(10)) == math.log(10))
ok("float(exp(-50)) ok",    abs(float(exp(-50)) - math.exp(-50)) <= 1e-37)
ok("float(R('1e-300'))",    float(R('1e-300')) == 1e-300)

# 9) ------------------- decimales: dígito a dígito vs mpmath -------------------
section("9. decimales() vs mpmath, cifra a cifra")
def cifras(name, expr, mpfn, n):
    got = expr.decimales(n)
    with mp.workdps(n + 40):
        v = mpfn()
        idig = max(1, int(mp.floor(mp.log10(abs(v)))) + 1) if v != 0 else 1
        s = mp.nstr(v, n + idig + 15, strip_zeros=False)
    ref = str(Decimal(s).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))
    ok(name, got[:-1] == ref[:-1], f"\n   got={got[-30:]}\n   ref={ref[-30:]}")

cifras("PI 100",     PI,       lambda: mp.pi,      100)
cifras("E 100",      E,        lambda: mp.e,       100)
cifras("LN2 80",     LN2,      lambda: mp.log(2),  80)
cifras("raiz2 100",  raiz(2),  lambda: mp.sqrt(2), 100)
cifras("exp(2) 60",  exp(2),   lambda: mp.e**2,    60)
cifras("sen(1) 60",  sen(1),   lambda: mp.sin(1),  60)

# headline: PI a 1000 cifras + timing
section("10. PI a 1000 decimales (headline) + tiempo")
t0 = time.perf_counter()
pi1000 = PI.decimales(1000)
dt = time.perf_counter() - t0
with mp.workdps(1040):
    ref1000 = str(Decimal(mp.nstr(mp.pi, 1015, strip_zeros=False))
                  .quantize(Decimal(1).scaleb(-1000), rounding=ROUND_HALF_UP))
ok("PI 1000 cifras == mpmath", pi1000[:-1] == ref1000[:-1])
print(f"  PI.decimales(1000) en {dt*1000:.1f} ms")
print(f"  primeras 64: {pi1000[:66]}")
print(f"  últimas  20: ...{pi1000[-20:]}")

# ----- RESUMEN -----
print("\n" + "=" * 70)
print(f"RESULTADO: {P} pasaron, {F} fallaron  (de {P+F} comprobaciones)")
if fails:
    print("FALLOS:")
    for n, d in fails:
        print(f"  - {n}: {d}")
    sys.exit(1)
print("TODO OK")
