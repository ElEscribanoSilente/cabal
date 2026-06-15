"""cabal — números reales exactos (computables), cero dependencias.

Contrato central: todo Real responde aprox(p) -> entero m con |m - x·2^p| <= 1.
La precisión se propaga hacia atrás por el grafo perezoso de la expresión; los
racionales viajan exactos (Fraction) cuando es posible. La igualdad de opacos
es semidecidible: si algo no se separa de 0 en TOPE bits, se lanza Inseparables
(honestidad computacional, no un bug).

Cada nodo lleva en comentario su cota de error demostrada.
"""
from __future__ import annotations

from fractions import Fraction
from math import isqrt, ldexp, isfinite

__version__ = "0.2.0"
__all__ = ["Real", "R", "PI", "E", "LN2", "raiz", "exp", "ln", "sen", "cos",
           "tan", "atan", "Inseparables", "TOPE"]

TOPE = 65536  # presupuesto de bits por defecto para decisiones (signo, dígitos)


class Inseparables(Exception):
    """No se pudo distinguir de cero con el presupuesto de bits dado."""


# ---------------- enteros auxiliares ----------------

def _rdiv(a: int, b: int) -> int:
    """round(a/b), b > 0, empates hacia +inf. |err| <= 1/2."""
    return (2 * a + b) // (2 * b)


def _tdiv(a: int, b: int) -> int:
    """trunc(a/b) hacia 0, b > 0. |err| < 1 y |resultado| <= |a/b| (garantiza terminación)."""
    q = abs(a) // b
    return -q if a < 0 else q


def _raj(m: int, k: int) -> int:
    """round(m/2^k); k <= 0 => desplazamiento exacto a la izquierda."""
    if k <= 0:
        return m << -k
    return (m + (1 << (k - 1))) >> k


def _tope(t):
    if t is None:
        return TOPE
    if isinstance(t, bool) or not isinstance(t, int):
        raise TypeError("tope debe ser un int (bits de presupuesto)")
    return t


def _esp(o):
    """float no finito (±inf/nan) -> o; en otro caso None."""
    return o if isinstance(o, float) and not isfinite(o) else None


_BLOQ = 10 ** 3000


def _dstr(k: int) -> str:
    """str(k) para k >= 0 sin el límite de CPython (4300 dígitos)."""
    if k.bit_length() <= 9900:           # < 10^2981: conversión directa segura
        return str(k)
    partes = []
    while k:
        k, r = divmod(k, _BLOQ)
        partes.append(r)
    s = str(partes.pop())
    return s + "".join(str(r).zfill(3000) for r in reversed(partes))


# ---------------- núcleo ----------------

class Real:
    """Real computable perezoso. Subclases implementan _calc(p)."""
    __slots__ = ("_p", "_m", "_fr")

    def __init__(self, fr: "Fraction | None" = None):
        self._p = None      # mejor precisión conocida
        self._m = 0         # aproximación cacheada a _p
        self._fr = fr       # valor racional exacto, si se conoce

    # -- contrato --
    def _calc(self, p: int) -> int:
        raise NotImplementedError

    def aprox(self, p: int) -> int:
        """Entero m con |m - x·2^p| <= 1."""
        fr = self._fr
        if fr is not None:  # exacto: err <= 1/2
            n, d = fr.numerator, fr.denominator
            return _rdiv(n << p, d) if p >= 0 else _rdiv(n, d << -p)
        if self._p is not None and self._p >= p:
            # cache: err <= 2^(p-_p) + 1/2 <= 1
            return self._m if self._p == p else _raj(self._m, self._p - p)
        m = self._calc(p)
        if self._p is None or p > self._p:
            self._p, self._m = p, m
        return m

    # -- cotas y sondas --
    def _cota(self) -> int:
        """b con |x| <= 2^b (barato, nunca falla)."""
        return (abs(self.aprox(0)) + 1).bit_length()

    def _sonda(self, tope: int):
        """(p, m) con |m| >= 4, o Inseparables si no se separa de 0."""
        fr = self._fr
        if fr is not None:
            if fr == 0:
                raise Inseparables("cero exacto")
            p = 4
            m = self.aprox(4)
            while abs(m) < 4:  # racional != 0: termina siempre
                p *= 2
                m = self.aprox(p)
            return p, m
        p = self._p if self._p is not None else 0
        m = self._m if self._p is not None else self.aprox(0)
        while abs(m) < 4:
            p = 8 if p < 8 else 2 * p
            if p > tope:                     # presupuesto estricto: nunca sondea más allá
                raise Inseparables(f"no se separa de 0 con presupuesto de {tope} bits")
            m = self.aprox(p)
        return p, m

    def _msd(self, tope: int) -> int:
        """k con |x| >= 2^k."""
        p, m = self._sonda(tope)
        return (abs(m) - 1).bit_length() - 1 - p  # |x| >= (|m|-1)/2^p >= 2^k

    # -- decisiones --
    def signo(self, tope=None) -> int:
        """-1/0/+1 certificado. Inseparables si es opaco e indistinguible de 0."""
        fr = self._fr
        if fr is not None:
            return (fr > 0) - (fr < 0)
        _, m = self._sonda(_tope(tope))
        return 1 if m > 0 else -1

    def _signo_o(self, tope):
        try:
            return self.signo(tope)
        except Inseparables:
            return None

    def iguales_hasta(self, otro, bits: int) -> bool:
        """Total. True => |self-otro| <= 2^(1-bits); False => |self-otro| >= 2^(-bits)."""
        return abs((self - _R(otro)).aprox(bits)) <= 1

    def intervalo(self, bits: int):
        """Cerco racional certificado: (lo, hi) Fraction con lo <= x <= hi, ancho 2^(1-bits)."""
        m = self.aprox(bits)
        e = Fraction(2) ** -bits
        return ((m - 1) * e, (m + 1) * e)

    def decimales(self, n: int = 15, tope=None) -> str:
        """n decimales correctamente redondeados (empates exactos hacia +inf)."""
        if n < 0:
            raise ValueError("n >= 0")
        v = self * (10 ** n) if n else self
        fr = v._fr
        if fr is not None:
            k = (2 * fr.numerator + fr.denominator) // (2 * fr.denominator)
        else:
            t, k = _tope(tope), None
            p = max(8, (n * 27) // 8 + 16)   # ~3.375 bits/dígito: 1 pasada típica
            if p > t:
                raise Inseparables(
                    f"presupuesto insuficiente: n={n} pide ~{p} bits > tope={t} "
                    "(sube tope= o cabal.TOPE)")
            while p <= t:
                m = v.aprox(p)
                a, b = _raj(m - 1, p), _raj(m + 1, p)  # cerco [m-1, m+1]/2^p
                if a == b:
                    k = a
                    break
                p *= 2
            if k is None:
                raise Inseparables(f"dígito ambiguo tras {t} bits (¿empate decimal de un opaco?)")
        s = "-" if k < 0 else ""
        k = abs(k)
        if n == 0:
            return s + _dstr(k)
        ent, dec = divmod(k, 10 ** n)
        ds = _dstr(dec)
        return f"{s}{_dstr(ent)}.{'0' * (n - len(ds))}{ds}"

    # -- conversiones --
    def __float__(self):
        try:
            p, m = self._sonda(2200)  # doblando llega a 2048 bits: cubre 2^-1074
        except Inseparables:
            return 0.0  # |x| < 2^-1098: bajo el subnormal mínimo
        if abs(m).bit_length() < 56:
            p += 56 - abs(m).bit_length()
            m = self.aprox(p)
        s = -1.0 if m < 0 else 1.0
        a = abs(m)
        bl = a.bit_length()
        if bl > 64:
            sh = bl - 64
            return s * ldexp(float(a >> sh), sh - p)
        return s * ldexp(float(a), -p)

    def __repr__(self):
        try:
            return f"Real({self.decimales(12, tope=4096)}…)"
        except Inseparables:
            return "Real(≈0, inseparable)"
        except (ValueError, ZeroDivisionError) as e:
            return f"Real(<dominio: {e}>)"

    # -- álgebra (tipo ajeno => NotImplemented: Python prueba el operador reflejado) --
    def __add__(self, o):
        return _Suma(self, _R(o)) if isinstance(o, _NUM) else NotImplemented
    __radd__ = __add__

    def __neg__(self):
        return _Neg(self)

    def __pos__(self):
        return self

    def __sub__(self, o):
        return _Suma(self, _Neg(_R(o))) if isinstance(o, _NUM) else NotImplemented

    def __rsub__(self, o):
        return _Suma(_R(o), _Neg(self)) if isinstance(o, _NUM) else NotImplemented

    def __mul__(self, o):
        return _Mul(self, _R(o)) if isinstance(o, _NUM) else NotImplemented
    __rmul__ = __mul__

    def __truediv__(self, o):
        return _Mul(self, _Inv(_R(o))) if isinstance(o, _NUM) else NotImplemented

    def __rtruediv__(self, o):
        return _Mul(_R(o), _Inv(self)) if isinstance(o, _NUM) else NotImplemented

    def __abs__(self):
        return _Abs(self)

    def __pow__(self, o):
        if not isinstance(o, _NUM):
            return NotImplemented
        if isinstance(o, Real) and o._fr is not None:
            o = o._fr                # exponente Real racional: atajo exacto
        if isinstance(o, float):
            if not isfinite(o):
                raise ValueError("float no finito")
            o = Fraction(o)          # 2.0 -> potencia entera; 0.5 -> raíz
        if isinstance(o, int):
            return _pot_ent(self, o)
        if isinstance(o, Fraction):
            if o.denominator == 1:
                return _pot_ent(self, o.numerator)
            if o == Fraction(1, 2):
                return raiz(self)
        return exp(_R(o) * ln(self))  # x > 0 (semidecidible)

    def __rpow__(self, o):
        return _R(o) ** self if isinstance(o, _NUM) else NotImplemented

    # -- orden (semidecidible para opacos iguales; ±inf/nan a la Python) --
    def __lt__(self, o):
        if not isinstance(o, _NUM):
            return NotImplemented
        e = _esp(o)
        if e is not None:
            return e > 0 if e == e else False   # x < +inf; nada con nan
        return (self - _R(o)).signo() < 0

    def __gt__(self, o):
        if not isinstance(o, _NUM):
            return NotImplemented
        e = _esp(o)
        if e is not None:
            return e < 0 if e == e else False
        return (self - _R(o)).signo() > 0

    def __le__(self, o):
        if not isinstance(o, _NUM):
            return NotImplemented
        e = _esp(o)
        if e is not None:
            return e > 0 if e == e else False   # igualdad con ±inf es falsa
        return (self - _R(o)).signo() <= 0

    def __ge__(self, o):
        if not isinstance(o, _NUM):
            return NotImplemented
        e = _esp(o)
        if e is not None:
            return e < 0 if e == e else False
        return (self - _R(o)).signo() >= 0

    def __eq__(self, o):
        if not isinstance(o, _NUM):
            return NotImplemented
        if _esp(o) is not None:
            return False
        d = self - _R(o)
        if d._fr is not None:
            return d._fr == 0
        return d.signo() == 0  # opaco: False si se separa; Inseparables si no

    def __bool__(self):
        """x != 0 certificado: semidecidible como ==, Inseparables si opaco ~ 0."""
        return self.signo() != 0

    __hash__ = None  # mutable-perezoso y con igualdad semidecidible: no hashable


def R(v) -> Real:
    """Constructor: Real | int | Fraction | str decimal exacto ('0.1') | float (su valor binario exacto)."""
    if isinstance(v, Real):
        return v
    if isinstance(v, (int, Fraction)):
        return _Cte(Fraction(v))
    if isinstance(v, float):
        if not isfinite(v):
            raise ValueError("float no finito")
        return _Cte(Fraction(v))
    if isinstance(v, str):
        return _Cte(Fraction(v))
    raise TypeError(f"no convertible a Real: {type(v).__name__}")


_R = R

_NUM = (Real, int, float, Fraction)   # operandos válidos en operadores binarios


# ---------------- nodos de campo ----------------

class _Cte(Real):
    __slots__ = ()


class _Suma(Real):
    __slots__ = ("a", "b")

    def __init__(self, a, b):
        fa, fb = a._fr, b._fr
        super().__init__(fa + fb if fa is not None and fb is not None else None)
        self.a, self.b = a, b

    def _calc(self, p):
        # err <= (1+1)/4 + 1/2 <= 1
        return _rdiv(self.a.aprox(p + 2) + self.b.aprox(p + 2), 4)


class _Neg(Real):
    __slots__ = ("a",)

    def __init__(self, a):
        super().__init__(-a._fr if a._fr is not None else None)
        self.a = a

    def _calc(self, p):
        return -self.a.aprox(p)


class _Abs(Real):
    __slots__ = ("a",)

    def __init__(self, a):
        super().__init__(abs(a._fr) if a._fr is not None else None)
        self.a = a

    def _calc(self, p):
        return abs(self.a.aprox(p))  # ||m|-|x·2^p|| <= |m-x·2^p| <= 1


class _Des(Real):
    """x·2^k (exacto)."""
    __slots__ = ("a", "k")

    def __init__(self, a, k):
        super().__init__(a._fr * Fraction(2) ** k if a._fr is not None else None)
        self.a, self.k = a, k

    def _calc(self, p):
        return self.a.aprox(p + self.k)


class _Mul(Real):
    __slots__ = ("a", "b")

    def __init__(self, a, b):
        fa, fb = a._fr, b._fr
        super().__init__(fa * fb if fa is not None and fb is not None else None)
        self.a, self.b = a, b

    def _calc(self, p):
        ca, cb = self.a._cota(), self.b._cota()      # |a|<=2^ca, |b|<=2^cb
        pa, pb = p + cb + 4, p + ca + 4
        # err <= 2^-4 + 2^-4 + eps + 1/2 < 1
        return _raj(self.a.aprox(pa) * self.b.aprox(pb), pa + pb - p)


class _Inv(Real):
    __slots__ = ("a",)

    def __init__(self, a):
        fr = a._fr
        if fr is not None and fr == 0:
            raise ZeroDivisionError("división entre cero exacto")
        super().__init__(1 / fr if fr is not None else None)
        self.a = a

    def _calc(self, p):
        k = self.a._msd(TOPE)                        # |a| >= 2^k
        if p - k <= -1:
            return 0                                 # |2^p/a| <= 2^(p-k) <= 1/2
        pa = max(p - 2 * k + 4, 2 - k)
        ma = self.a.aprox(pa)                        # |ma| >= 2^(k+pa) - 1 >= 2^(k+pa-1)
        s = -1 if ma < 0 else 1
        # err <= 2^(p-2k-pa+1) + 1/2 <= 2^-3 + 1/2 < 1
        return s * _rdiv(1 << (p + pa), abs(ma))


class _Sqrt(Real):
    __slots__ = ("a",)

    def __init__(self, a):
        fr = a._fr
        nf = None
        if fr is not None:
            if fr < 0:
                raise ValueError("raíz de negativo")
            sn, sd = isqrt(fr.numerator), isqrt(fr.denominator)
            if sn * sn == fr.numerator and sd * sd == fr.denominator:
                nf = Fraction(sn, sd)                # cuadrado perfecto: exacto
        super().__init__(nf)
        self.a = a

    def _calc(self, p):
        pa = 2 * p + 4
        ma = self.a.aprox(pa)
        if ma < -1:
            raise ValueError("raíz de negativo (certificado)")
        if ma <= 0:
            return 0                                 # sqrt(x)·2^p <= 2^-2
        # sqrt(x)·2^p = sqrt(ma+e)/4; isqrt(ma<<8) = 16·sqrt(ma) ± 1
        # err <= (1 + 16·(1/(2·sqrt(ma))))/64 + 1/2 < 1
        return _rdiv(isqrt(ma << 8), 64)


def _pot_ent(x: Real, n: int) -> Real:
    if n == 0:
        return R(1)
    if n < 0:
        return _Inv(_pot_ent(x, -n))
    r, b = None, x
    while n:
        if n & 1:
            r = b if r is None else _Mul(r, b)
        n >>= 1
        if n:
            b = _Mul(b, b)
    return r


# ---------------- series enteras ----------------
# Patrón común: trabajar a w = p + 8 + bitlen bits; el exceso absorbe
# T términos truncados (T < 2^bitlen(w)), deriva geométrica y cola. err total <= 1.

class _SerieRecip(Real):
    """atan(1/n) (alt) / atanh(1/n), n >= 2 entero. |valor| < 0.55."""
    __slots__ = ("n", "alt")

    def __init__(self, n, alt):
        super().__init__()
        self.n, self.alt = n, alt

    def _calc(self, p):
        if p < 2:
            return _raj(self._calc(4), 4 - p)
        w = p + 8
        w += w.bit_length()
        n2 = self.n * self.n
        cur = (1 << w) // self.n
        s, i, sg = 0, 1, 1
        while cur:
            s += sg * (cur // i)
            cur //= n2
            i += 2
            if self.alt:
                sg = -sg
        return _raj(s, w - p)


class _SerieImpar(Real):
    """suma u^(2k+1)/(2k+1): atan (alt, |u| <= 0.78) / atanh (|u| <= 0.5)."""
    __slots__ = ("a", "alt")

    def __init__(self, a, alt):
        super().__init__()
        self.a, self.alt = a, alt

    def _calc(self, p):
        if p < 2:
            return _raj(self._calc(4), 4 - p)
        w = p + 8
        w += w.bit_length()
        mu = self.a.aprox(w)
        m2 = _rdiv(mu * mu, 1 << w)                  # u²·2^w ± 2
        s, t, i, sg = 0, mu, 1, 1
        while t:
            s += sg * _rdiv(t, i)
            t = _tdiv(t * m2, 1 << w)                # trunc: |t| decrece estrictamente
            i += 2
            if self.alt:
                sg = -sg
        return _raj(s, w - p)


class _SerieExp(Real):
    """exp(y), |y| <= 1/2."""
    __slots__ = ("a",)

    def __init__(self, a):
        super().__init__()
        self.a = a

    def _calc(self, p):
        if p < 2:
            return _raj(self._calc(4), 4 - p)
        w = p + 8
        w += w.bit_length()
        my = self.a.aprox(w)
        s = t = 1 << w
        k = 1
        while t:
            t = _tdiv(t * my, k << w)
            s += t
            k += 1
        return _raj(s, w - p)


class _SerieTrig(Real):
    """sen(r) / cos(r), |r| <= 0.95."""
    __slots__ = ("a", "es_sen")

    def __init__(self, a, es_sen):
        super().__init__()
        self.a, self.es_sen = a, es_sen

    def _calc(self, p):
        if p < 2:
            return _raj(self._calc(4), 4 - p)
        w = p + 8
        w += w.bit_length()
        mr = self.a.aprox(w)
        m2 = _rdiv(mr * mr, 1 << w)
        if self.es_sen:
            t, k = mr, 2          # r, luego /(2·3), /(4·5)...
        else:
            t, k = 1 << w, 1      # 1, luego /(1·2), /(3·4)...
        s, sg = 0, 1
        while t:
            s += sg * t
            t = _tdiv(t * m2, (k * (k + 1)) << w)
            k += 2
            sg = -sg
        return _raj(s, w - p)


# ---------------- funciones compuestas ----------------

class _Exp(Real):
    """exp(x) = exp(x/2^j)^(2^j), con |x/2^j| < 1/2."""
    __slots__ = ("a", "j", "ub")

    def __init__(self, x):
        super().__init__()
        m = abs(x.aprox(4))                          # |x| <= (m+1)/16
        self.j = max(0, (m + 2).bit_length() - 3)    # |x/2^j| < 1/2
        self.ub = 3 * (m + 1) // 32 + 2              # |log2 e^x| <= ub
        self.a = _SerieExp(_Des(x, -self.j))

    def _calc(self, p):
        if self.j == 0:
            return self.a.aprox(p)
        W = max(p, 0) + 2 * self.ub + self.j + 12    # error relativo final <= 2^-(p+ub+1)
        v = self.a.aprox(W)
        for _ in range(self.j):
            v = _rdiv(v * v, 1 << W)
        return _raj(v, W - p)


class _Ln(Real):
    """ln(x) = 2·atanh((m-1)/(m+1)) + e·ln2, m = x/2^e ∈ [0.75, 2.5)."""
    __slots__ = ("a", "expr")

    def __init__(self, a):
        super().__init__()
        self.a, self.expr = a, None

    def _arm(self):
        p, m = self.a._sonda(TOPE)
        if m < 0:
            raise ValueError("ln de negativo (certificado)")
        e = m.bit_length() - 1 - p
        mr = _Des(self.a, -e)
        u = (mr - 1) * _Inv(mr + 1)                  # |u| <= 3/7
        serie = _Des(_SerieImpar(u, False), 1)
        self.expr = serie + e * LN2 if e else serie

    def _calc(self, p):
        if self.expr is None:
            self._arm()
        return self.expr.aprox(p)


class _Trig(Real):
    """Reduce x = r + n·pi/2 con |r| <= 0.95 y despacha a la serie con signo."""
    __slots__ = ("a", "es_sen", "expr")

    def __init__(self, a, es_sen):
        super().__init__()
        self.a, self.es_sen, self.expr = a, es_sen, None

    def _arm(self):
        n = _raj((self.a * _DOSPI_INV).aprox(4), 4)  # |n - x·2/pi| <= 9/16
        r = self.a if n == 0 else self.a - PI * R(Fraction(n, 2))
        q = n & 3
        if self.es_sen:
            serie = _SerieTrig(r, q % 2 == 0)        # sen,cos,-sen,-cos
            neg = q >= 2
        else:
            serie = _SerieTrig(r, q % 2 == 1)        # cos,-sen,-cos,sen
            neg = q in (1, 2)
        self.expr = _Neg(serie) if neg else serie

    def _calc(self, p):
        if self.expr is None:
            self._arm()
        return self.expr.aprox(p)


# ---------------- API pública ----------------

def raiz(x) -> Real:
    return _Sqrt(_R(x))


def exp(x) -> Real:
    x = _R(x)
    if x._fr is not None and x._fr == 0:
        return R(1)
    return _Exp(x)


def ln(x) -> Real:
    x = _R(x)
    fr = x._fr
    if fr is not None:
        if fr <= 0:
            raise ValueError("ln requiere x > 0")
        if fr == 1:
            return R(0)
    return _Ln(x)


def sen(x) -> Real:
    x = _R(x)
    if x._fr is not None and x._fr == 0:
        return R(0)
    return _Trig(x, True)


def cos(x) -> Real:
    x = _R(x)
    if x._fr is not None and x._fr == 0:
        return R(1)
    return _Trig(x, False)


def tan(x) -> Real:
    x = _R(x)
    return _Mul(sen(x), _Inv(cos(x)))


def atan(x) -> Real:
    """Tres ramas con decisión certificada (las zonas de duda caen en la rama válida)."""
    x = _R(x)
    fr = x._fr
    if fr is not None:
        if fr == 0:
            return R(0)
        af = abs(fr)
        rama = "t" if af <= Fraction(3, 4) else ("r" if af >= Fraction(3, 2) else "m")
        s = 1 if fr > 0 else -1
    else:
        ax = _Abs(x)
        s1 = (ax - 1)._signo_o(64)
        if s1 is None:
            rama = "m"                                   # |x| = 1 ± 2^-63
        elif s1 < 0:
            rama = "t" if (ax - R(Fraction(3, 4)))._signo_o(64) in (None, -1) else "m"
        else:
            rama = "r" if (ax - R(Fraction(3, 2)))._signo_o(64) == 1 else "m"
        s = x.signo() if rama == "r" else 0              # |x| > 1: separable rápido
    if rama == "t":
        return _SerieImpar(x, True)                      # |x| <= 3/4 + eps
    if rama == "m":                                      # ángulo mitad: |w| <= 0.54
        w = x * _Inv(1 + raiz(1 + x * x))
        return _Des(_SerieImpar(w, True), 1)
    return R(Fraction(s, 2)) * PI - _SerieImpar(_Inv(x), True)  # |1/x| <= 2/3 + eps


# ---------------- constantes ----------------

PI = _SerieRecip(5, True) * 16 - _SerieRecip(239, True) * 4   # Machin
LN2 = _Des(_SerieRecip(3, False), 1)                          # 2·atanh(1/3)
E = exp(1)
_DOSPI_INV = _Des(_Inv(PI), 1)                                # 2/pi
