# Changelog

Todas las versiones de `cabal`. Formato basado en [Keep a Changelog](https://keepachangelog.com/es/).

## 0.2.1 — 2026-06-15

### Corregido
- **`Real.__float__` ahora devuelve siempre el `double` más cercano** (correctamente
  redondeado, *ties-to-even*). Antes podía quedar a **1 ULP** del valor correcto por un
  doble redondeo interno: ~2.8 % de los racionales y ~5.7 % de los opacos. El núcleo
  certificado (`aprox`, `decimales`, `intervalo`, `signo`, comparaciones) **nunca estuvo
  afectado** —el bug vivía solo en la conversión con pérdida a `float`—.
- Detectado por *fuzzing* diferencial propio; blindado con la regresión
  [`bench/float_redondeo.py`](bench/float_redondeo.py) (~330 000 casos contra
  `float(Fraction)` y mpmath, 0 fallos). De hallazgo a corrección en la misma sesión.

## 0.2.0 — 2026-06-15

- Primera publicación en PyPI: `pip install cabal`.
- Aritmética real exacta (reales computables, estilo Boehm) con contrato
  `|aprox(p) − x·2^p| ≤ 1` por nodo, cero dependencias, un solo archivo.
