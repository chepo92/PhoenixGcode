# PhoenixGCode

> **A universal G-code analysis and failed print recovery library.**

PhoenixGCode es una biblioteca Python para analizar, interpretar y transformar archivos G-code de impresoras 3D.

Su primer objetivo es permitir la recuperación de impresiones fallidas mediante la generación de un nuevo G-code que continúe la impresión desde una altura determinada, reconstruyendo automáticamente el estado de la impresora.

Sin embargo, la recuperación es solamente la primera aplicación. La arquitectura está diseñada para convertirse en un motor general de análisis y transformación de G-code.

---

# Filosofía

La mayoría de las herramientas existentes modifican archivos G-code como si fueran texto.

PhoenixGCode sigue un enfoque diferente.

Antes de modificar cualquier archivo, reconstruye virtualmente el estado de ejecución de la impresora.

En otras palabras:

No modifica un archivo hasta comprender qué significa cada instrucción.

---

# Objetivos

- Analizar archivos G-code completos.
- Interpretar el estado de ejecución de la impresora.
- Reconstruir posiciones, temperaturas y modos de operación.
- Generar transformaciones seguras.
- Mantener una API reutilizable para otras aplicaciones.

---

# Características

## Análisis

- Parser completo de G-code.
- Interpretación del estado de la impresora.
- Reconstrucción de movimientos.
- Reconstrucción del extrusor.
- Detección automática de capas.
- Construcción de índices internos.

## Recovery

- Recuperación desde una altura Z medida.
- Selección de candidatos de recuperación.
- Reconstrucción automática del estado.
- Recovery Plan editable.
- Estrategias configurables de recuperación.
- Generación automática de un nuevo G-code.

## Arquitectura

- Biblioteca independiente.
- API pública.
- CLI oficial.
- Integraciones desacopladas.
- Preparado para múltiples firmwares.

---

# Principios

## Comprender antes de transformar

Toda modificación debe basarse en un modelo interno del G-code.

Nunca se modificará texto directamente.

---

## Automatización supervisada

Phoenix detecta automáticamente toda la información que puede inferirse del G-code.

El usuario siempre podrá revisar y modificar los parámetros antes de generar un nuevo archivo.

---

## Responsabilidad única

Cada módulo realiza solamente una tarea.

Ejemplos:

Reader

Tokenizer

Parser

Interpreter

Analyzer

Transformer

Writer

---

## El núcleo no depende de interfaces

La biblioteca no conoce:

- Cura
- OctoPrint
- Print2Go
- CLI

Todas las interfaces consumen la misma API pública.

---

# Arquitectura

                    PhoenixGCode

                         │

                    Public API

                         │

        ┌────────────────┼────────────────┐

        │                │                │

        ▼                ▼                ▼

     Reader         Interpreter     Transformer

        │                │                │

        ▼                ▼                ▼

    Tokenizer      Execution State   Recovery

        │                │           Future Tools

        ▼                │

      Parser             ▼

        │          Document Model

        └───────────────┬───────────────┐

                        ▼               ▼

                  Analyzer         Writer

                        │

                        ▼

                Layer Index

                Z Index

                Snapshot Index

---

# Estructura del proyecto

phoenixgcode/

    model/

    reader/

    tokenizer/

    parser/

    interpreter/

    analyzer/

    transformer/

        recovery/

    writer/

    profiles/

    utils/

frontends/

    cli/

    cura/

    print2go/

    octoprint/

tests/

docs/

examples/

---

# Pipeline

Archivo G-code

↓

Reader

↓

Tokenizer

↓

Parser

↓

Document Model

↓

Interpreter

↓

Execution Timeline

↓

Analyzer

↓

Recovery Planner

↓

Recovery Plan

↓

Usuario revisa

↓

Recovery Builder

↓

Writer

↓

Recovery.gcode

---

# Recovery Workflow

1. Seleccionar el archivo G-code original.

2. Analizar completamente el archivo.

3. Reconstruir el estado de ejecución.

4. Ingresar la altura Z medida.

5. Buscar candidatos de recuperación.

6. Construir un Recovery Plan.

7. Permitir modificar parámetros.

8. Generar el nuevo G-code.

---

# Recovery Plan

El Recovery Plan contiene toda la información necesaria antes de generar un nuevo archivo.

Incluye:

- Punto de recuperación.
- Layer seleccionado.
- Altura Z.
- Temperaturas detectadas.
- Modo de extrusión.
- Ventilador.
- Último valor de E.
- Estrategia de recuperación.
- Configuración editable.
- Archivo de salida.

El usuario siempre podrá revisarlo antes de continuar.

---

# Recovery Strategies

Inicialmente se soportarán:

- Manual Position
- Home XY
- Home XYZ
- Custom Script

La arquitectura permitirá agregar nuevas estrategias sin modificar el núcleo.

---

# Compatibilidad

Diseñado para:

- Marlin (MVP)

Arquitectura preparada para:

- Klipper
- RepRapFirmware
- Bambu
- Otros perfiles futuros

---

# Interfaces oficiales

PhoenixGCode ofrece dos interfaces oficiales.

## API Python

Para integraciones directas.

Utilizada por:

- Cura Plugin
- Print2Go
- OctoPrint

## CLI

Pensada para:

- Usuarios
- Scripts
- Automatización
- Integraciones mediante línea de comandos

---

# CLI

La CLI soportará dos modos.

## Interactivo

Asistente paso a paso para usuarios.

Ejemplo:

phoenix recover dragon.gcode

La aplicación solicitará únicamente los datos necesarios.

---

## Batch

Pensado para automatización.

Ejemplo:

phoenix recover dragon.gcode --z 83.42 --candidate 2 --home xy

En este modo nunca se solicitará información interactiva.

---

# Integraciones

Integraciones oficiales previstas:

- CLI
- Ultimaker Cura
- Print2Go
- OctoPrint

Integraciones mediante CLI:

- PrusaSlicer
- OrcaSlicer
- Bambu Studio

Todas las integraciones utilizarán exclusivamente la API pública o la CLI oficial.

---

# Calidad

- Python 3.11+
- Type Hints
- Dataclasses
- Logging
- Pruebas unitarias
- Sin variables globales
- Arquitectura modular

---

# Estado del proyecto

Actualmente en desarrollo.

Primera meta:

Recovery de impresiones fallidas.

Las siguientes funcionalidades se desarrollarán sobre el mismo motor de análisis.

---

# Roadmap

## v0.1

- Modelo de datos.
- Reader.
- Tokenizer.
- Parser.
- Interpreter.
- Analyzer.

## v0.2

- Recovery Planner.
- Recovery Builder.
- Writer.

## v0.3

- CLI oficial.
- Recovery Wizard.
- Pruebas con G-code reales.

## v0.4

- Plugin para Ultimaker Cura.

## v0.5

- Integración con Print2Go.

## v0.6

- Plugin para OctoPrint.

## Futuro

- Nuevos perfiles de firmware.
- Más transformaciones de G-code.
- Optimización de movimientos.
- Validación de G-code.
- Estadísticas de impresión.
- Conversión entre dialectos.
- Integraciones adicionales.
- Interfaz TUI.
- Interfaz Web.

---

# Lema

PhoenixGCode

A universal G-code analysis and failed print recovery library.