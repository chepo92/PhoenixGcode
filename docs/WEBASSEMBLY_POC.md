# Proof of Concept: PhoenixGCode en WebAssembly (Pyodide)

## 1. Resumen Ejecutivo
Esta Prueba de Concepto (PoC) valida la viabilidad técnica de ejecutar la biblioteca **PhoenixGCode** directamente dentro del navegador cliente mediante WebAssembly utilizando **Pyodide** (CPython 3.12 compilado a WASM).

Toda la lógica de análisis se ejecuta de forma local en el navegador del usuario, sin requerir servidor backend ni enviar datos a la red.

---

## 2. Arquitectura Utilizada

```text
[ NAVEGADOR WEB (Cliente Estático) ]
│
├── JavaScript ES6 (App Controller & Bridge)
│     │
│     ├── Carga Pyodide Core & Micropip
│     ├── Instala phoenixgcode-*.whl generado en build
│     └── Invoca PhoenixGCodeAPI via Pyodide Bridge
│
└── Pyodide Runtime (WASM Virtual Engine)
      │
      ├── Micropip Package Manager (chardet, etc.)
      └── PhoenixGCode Core (phoenixgcode.api)
            ├── GCodeReader & Tokenizer
            ├── GCodeParser & Interpreter
            └── GCodeAnalyzer