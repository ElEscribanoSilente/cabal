# cabal

Números reales **exactos** (computables) en Python puro, cero dependencias, un solo archivo.

Cada `Real` es un nodo perezoso de un grafo de expresión que cumple un contrato verificable:

```
x.aprox(p) -> entero m  con  |m − x·2^p| ≤ 1        (para todo p ∈ ℤ)
```

La precisión se propaga hacia atrás bajo demanda. No eliges una precisión de trabajo y rezas:
pides dígitos y el grafo calcula lo necesario para **certificarlos**.

```python
from cabal import R, PI, E, raiz, exp, ln, sen

R("0.1") + R("0.2") == R("0.3")        # True — decidible y exacto (atajo racional)
PI.decimales(1000)                      # 1000 decimales correctamente redondeados (~ms)
exp(ln(R("1234.5678"))).decimales(30)   # '1234.567800000000000000000000000000'
PI.intervalo(100)                       # cerco racional certificado: (Fraction, Fraction), ancho 2^-99
(raiz(2)**2 - 2).signo(tope=1024)       # Inseparables: igualdad de opacos = semidecidible. Honesto.
```

## Garantías y cómo se verifican

- **Contrato ≤ 1 ulp por nodo**, con la cota de error demostrada en comentario junto a cada
  implementación, y verificado empíricamente contra `Fraction` (oráculo exacto) en cientos de
  árboles aleatorios de expresiones (`test_cabal.py`, ancla A1).
- **Dígitos decimales correctamente redondeados** (empates exactos hacia +∞), o `Inseparables`
  si el presupuesto no alcanza — nunca un dígito silenciosamente falso.
- **Atajo racional**: las subexpresiones racionales viajan como `Fraction`; igualdad y signo de
  racionales son decidibles y exactos. `R("0.1")` es 1/10 exacto, no el double más cercano.
- **Cercos exportables**: `intervalo(bits)` devuelve fracciones exactas `lo ≤ x ≤ hi` — un
  certificado que puedes verificar fuera de la librería.
- **Semidecidibilidad explícita**: el signo de un opaco igual a 0 no es computable (Teorema de
  Rice de fondo). `cabal` lo declara con `Inseparables` en vez de colgar o mentir.
- **Validación cruzada reproducible**: a 10 000 dígitos contra mpmath (π, e, ln 2, √2, sen 1, e^π),
  por fórmulas independientes en enteros puros (π vía atan(1/2)+atan(1/3), ln 2 vía Σ1/(k·2^k),
  e vía Σ1/k!), y en las fronteras adversariales de cada rama (reducción trigonométrica pegada a
  k·π/2, atan en ±3/4, ±1, ±3/2, ln junto a potencias de 2, subnormales de `float`). Arneses en el
  repo: `audit_cabal.py`, `audit2_cabal.py`, `stress_cabal.py` (usan mpmath; la librería, nada).

## Estado del arte (claims calibrados)

No es la primera aritmética real exacta. Es una síntesis distinta:

| | enfoque | deps | contrato verificado por tests | cercos racionales | igualdad |
|---|---|---|---|---|---|
| **cabal** | entero escalado (Boehm) + DAG memoizado | 0 | sí (vs `Fraction`) | sí | exacta en ℚ, semidecidible declarada |
| `reals` | fracciones continuas (Gosper) | 0 | no | no | implícita |
| `mpmath` | flotante de precisión fija | 0 | n/a (sin certificación) | no | tolerancia |
| `python-flint` (Arb) | bolas, C | C | n/a | sí | bolas |

El aporte es **incremental en concepto** (Boehm 1986) e **innovador en empaque**: contrato
falsable + atajo racional + semidecidibilidad como API + microlibrería auditable (~700 líneas).

## API

`R(v)` (int/Fraction/str-decimal/float), operadores `+ − × ÷ ** abs` (también reflejados:
`2 ** PI`), comparaciones (`±inf`/`nan` con la semántica de Python), `bool(x)` = «x ≠ 0 certificado»,
`raiz, exp, ln, sen, cos, tan, atan`, constantes `PI, E, LN2`. Métodos:
`aprox(p)`, `decimales(n)`, `intervalo(bits)`, `signo(tope)`, `iguales_hasta(otro, bits)`, `float()`.
Exponentes racionales (aunque lleguen como `Real` o `float` entero) usan el atajo exacto:
`(-R(2))**2.0 == 4` es decidible; el resto va por `exp(y·ln x)` y exige `x > 0`.

## Límites (léelos)

- Comparar dos opacos **iguales** —o `bool`/`if` de un cero opaco— lanza `Inseparables` al agotar
  `cabal.TOPE` (default 65 536 bits). Es matemática, no un bug.
- `decimales(n)` necesita ~3.4·n bits de presupuesto: con `TOPE` default el máximo es ~19 400
  dígitos; más allá, el error lo dice claro y basta subir `tope=`.
- Cadenas opacas de >~10³ nodos anidados dan `RecursionError` (límite de CPython; sube
  `sys.setrecursionlimit` si construyes grafos muy profundos).
- `raiz` de un opaco indistinguible de 0 devuelve ≈0 aunque el valor sea un negativo diminuto
  (se comporta como √max(x, 0)); un negativo *certificable* sí lanza `ValueError`.
- `exp` de argumentos enormes (|x| ≳ 10⁵) genera enteros del tamaño del resultado, y las torres
  (`exp(exp(exp(3)))`) son números de 10⁹ bits: cuelgan por aritmética, no por bug.
- Las series escalan O(p²): π a 40 000 dígitos ≈ 3 s; a 600 000, minutos. `raiz` es subcuadrática
  (10⁶ dígitos ≈ 11 s). El presupuesto `tope`/`TOPE` debe ser `int`; es estricto (nunca se sondea
  más allá).
- Sin soporte de `hash` (igualdad semidecidible ⇒ no hashable). No es thread-safe.
- Construir `exp/ln/sen/cos` evalúa una sonda barata del argumento.

## Autoría

Creado por **Escribano Silente**. Coautor: **esraderey**.

MIT. `python3 test_cabal.py` corre las 792 anclas sin dependencias; los arneses de auditoría y
estrés añaden ~3 400 verificaciones contra oráculos independientes.
