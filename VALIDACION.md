# Validación y rendimiento

**cabal** no promete exactitud: la **certifica**. Cada `Real` cumple un contrato verificable

```
x.aprox(p) → entero m    tal que    |m − x·2ᵖ| ≤ 1     para todo p ∈ ℤ
```

Pides la aproximación de `x` escalada por `2ᵖ` y recibes un entero que dista **a lo sumo 1** del valor verdadero. Este documento somete ese contrato a prueba empírica contra un oráculo **independiente** y mide cuánto cuesta la certificación frente a las alternativas.

Todo es reproducible con los scripts de [`bench/`](bench/). Los resultados de abajo se generaron validando **cabal 0.2.0 instalado desde PyPI**.

---

## Resumen

| | |
|---|---|
| Comprobaciones diferenciales vs mpmath | **3 599 / 3 599** ✓ — **0 fallos** |
| de ellas, árboles de expresión aleatorios | 3 476 — **0 violaciones del cerco** |
| π a 1 000 cifras | idéntico a mpmath · **≈ 2.6 ms** |
| Velocidad frente a mpmath | misma liga (**0.5× – 1.6×**) |
| Velocidad frente a `decimal` en `exp`/`ln` | hasta **~2 500× más rápido** |
| Tamaño | 1 archivo · ~700 líneas · **0 dependencias** |

---

## 1. Metodología: un oráculo independiente

Validar aritmética que se proclama exacta exige un juez **más preciso e independiente** que lo juzgado. Se usa [**mpmath**](https://mpmath.org) (precisión arbitraria, maduro, motor numérico de SymPy) como oráculo, y se cruza cada resultado por dos vías complementarias:

**(a) Contrato directo.** Para cada nodo y varios `p ∈ {0, 1, 8, 53, 120, 300, 1000}` bits se comprueba

```
|aprox(p) − v·2ᵖ| ≤ 1
```

donde `v` es el valor de mpmath calculado a `⌈0.30·p⌉ + 50` cifras (resolución muy por encima de `2⁻ᵖ`). Verifica el contrato **al pie de la letra**, en aritmética racional exacta.

**(b) Cerco certificado** — la prueba más fuerte. `expr.intervalo(bits)` devuelve un intervalo racional `[lo, hi]` con `lo ≤ x ≤ hi` y ancho `2^(1−bits)`. Se comprueba que el valor de mpmath **cae dentro**. No compara cifras (que dependen del modo de redondeo) sino **contención del valor verdadero dentro de una cota demostrada**: si cabal violara su contrato, el oráculo caería fuera del cerco.

---

## 2. Correctitud

### 2.1 · Suite curada — 123 comprobaciones · [`bench/diferencial.py`](bench/diferencial.py)

Cubre, todas verificadas contra mpmath:

- **Contrato** `|aprox(p) − x·2ᵖ| ≤ 1` de `p = 0` a `1000` bits (π, e, ln 2, exp, ln, raíz, sen, cos, atan).
- **Cerco certificado** conteniendo el valor verdadero en `exp(100)`, `ln(10¹⁰⁰)`, `sen(1000)` (reducción de argumento), `atan(100)`, `3^(1/3)`, `PI·E`, …
- **Exactitud racional**: `0.1 + 0.2 == 0.3` exacto (lo que el `float` no logra), `1/3` a 30 decimales, `2¹⁰⁰` exacto.
- **Identidades**: `sen²+cos² = 1`, `exp(ln x) = x`, `ln(ab) = ln a + ln b`, `raíz(x)² = x`, `tan = sen/cos`.
- **Honestidad computacional**: `raíz(2)² − 2` (exactamente 0 pero opaco) lanza `Inseparables` en `signo()`/`bool()`; `iguales_hasta` responde de forma total.
- **Errores de dominio**: `1/0`, `raíz(-1)`, `ln(0)`, `ln(-2)`, `R(inf)`, `R(nan)`.
- **`float()` correctamente redondeado**: `float(PI) == math.pi`, `float(E) == math.e`, … (igualdad bit a bit).
- **`decimales()` cifra a cifra** vs mpmath, hasta **π a 1 000 decimales** (coincidencia exacta).

```
RESULTADO: 123 pasaron, 0 fallaron  (de 123 comprobaciones)
```

### 2.2 · Fuzz diferencial — 3 476 árboles aleatorios · [`bench/fuzz.py`](bench/fuzz.py)

Se generan 4 000 árboles de expresión al azar (constantes racionales combinadas con `+ − × ÷`, `exp`, `ln`, `sen`, `cos`, `atan`, `raíz` y cuadrado; profundidad 1–4; semilla fija). Se evalúan **3 476** y se omiten **524** de forma legítima (dominio inválido como `ln(<0)`, o resultados inseparables de 0). En los 3 476:

```
0 violaciones del cerco · 0 errores inesperados
```

El valor verdadero cayó **siempre** dentro del intervalo certificado.

### 2.3 · Un error cazado y corregido (v0.2.1) · [`bench/float_redondeo.py`](bench/float_redondeo.py)

El *fuzzing* diferencial de arriba destapó un fallo real: `float(x)` no siempre devolvía
el `double` más cercano —quedaba a **1 ULP** por un doble redondeo interno (~2.8 % de los
racionales, ~5.7 % de los opacos)—. El núcleo certificado nunca estuvo afectado; el bug
vivía solo en la conversión con pérdida a `float`. Se corrigió en **0.2.1** (redondeo
correcto *ties-to-even*) y se blindó con una regresión que recorre **~330 000 casos** contra
`float(Fraction)` y mpmath sin un solo fallo. De hallazgo a *fix* en la misma sesión —ver
[`CHANGELOG.md`](CHANGELOG.md).

---

## 3. Rendimiento · [`bench/benchmark.py`](bench/benchmark.py)

**Tarea:** calcular un valor a **N cifras decimales correctas**. Competidores de precisión arbitraria en Python: **mpmath**, **`decimal`** (stdlib; sin π ni sen) y **SymPy**. Tiempos en **milisegundos**, mejor de varias corridas.

> **Equidad con mpmath.** mpmath *cachea* π y e. Para una comparación honesta de *cómputo desde cero*, la columna de mpmath se mide invalidando la caché por precisión, de modo que usa su **algoritmo nativo** (Chudnovsky para π) — no la ruta lenta `4·atan(1)`. Aun así, mpmath gana en π/e/ln abajo: no se le maquilla.

**N = 5 000 cifras**

| tarea | cabal | mpmath | decimal | sympy |
|:------|------:|-------:|--------:|------:|
| π     | 0.66  | **0.41** | —      | 0.45  |
| e     | 0.67  | **0.43** | 562    | 0.50  |
| √2    | **0.63** | 0.82  | 10.8   | 1.01  |
| ln 2  | 0.66  | **0.42** | 1 676  | 0.51  |
| sen 1 | **0.65** | 7.81  | —      | 8.15  |

**N = 1 000 cifras**

| tarea | cabal | mpmath | decimal | sympy |
|:------|------:|-------:|--------:|------:|
| π     | 0.05  | 0.04   | —       | 0.05  |
| e     | 0.05  | 0.03   | 13.5    | 0.04  |
| √2    | **0.05** | 0.08 | 0.42    | 0.09  |
| ln 2  | 0.05  | 0.04   | 19.1    | 0.05  |
| sen 1 | **0.05** | 0.42 | —       | 0.43  |

(Corrección: las primeras 40 cifras coinciden entre las cuatro librerías para los cinco valores.)

### Lectura honesta

- **cabal juega en la misma liga que mpmath** —el estándar maduro y optimizado de precisión arbitraria en Python puro—, casi siempre dentro de **0.5× – 1.6×**.
- mpmath gana por poco en sus rutinas más afinadas (π por Chudnovsky, `exp`, `log`): **~1.5×**.
- cabal **gana** en `sen` (**~12×**) y **arrasa** frente a `decimal` en transcendentales: `exp` a 5 000 cifras **0.67 ms vs 562 ms** (~840×), `ln` **0.66 ms vs 1 676 ms** (~2 500×).
- El valor de cabal no es el milisegundo: es **certificar** cada resultado (error ≤ 1 ulp, demostrado nodo a nodo) en **~700 líneas de Python puro y cero dependencias**, siendo a la vez **competitivo en velocidad** con librerías mucho mayores que **no** certifican —en ellas fijas la precisión y confías en los dígitos de guarda—.

---

## 4. Reproducir

```bash
pip install cabal mpmath sympy     # sympy solo lo usa el benchmark
# desde la raíz del repositorio:
python bench/diferencial.py        # 123 comprobaciones curadas vs mpmath
python bench/fuzz.py               # 3 476 árboles de expresión aleatorios
python bench/float_redondeo.py     # redondeo correcto de float() (regresión 0.2.1)
python bench/benchmark.py          # tabla de rendimiento
```

## 5. Entorno

Windows 11 · Python 3.13.2 · cabal 0.2.1 · mpmath 1.3.0 · sympy 1.14.0.
Los **tiempos absolutos varían por máquina**; lo relevante son las proporciones.
