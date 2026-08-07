# PhoenixGCode

> **A universal G-code analysis and failed print recovery library.**

PhoenixGCode is an open-source Python library for analyzing G-code and recovering failed FDM 3D prints.

Its primary goal is to eliminate the need to manually edit G-code files after a failed print by providing a reliable, reusable recovery engine that can be integrated into desktop applications, slicers, web applications and automation tools.

The first official feature of PhoenixGCode is **Failed Print Recovery**.

---

# Why PhoenixGCode?

Anyone who has spent 20, 30 or even 50 hours printing a large model knows the feeling:

- Power outage
- Filament run-out
- Clogged nozzle
- Layer shift
- Accidental printer stop
- Firmware reset

The print fails just before completion.

Traditionally, recovering such a print requires manually editing thousands of lines of G-code, understanding extrusion state, removing startup sequences and hoping nothing was missed.

PhoenixGCode automates that process.

---

# Features

Current features:

- Analyze G-code files
- Detect print metadata
- Detect layer structure
- Recover failed prints from a measured Z height
- Generate recovery G-code
- Browser-based execution using Pyodide
- Pure Python Core
- Platform independent

Planned features:

- Automatic recovery assistant
- G-code validation
- G-code optimization
- Semantic G-code comparison
- Plugin for Ultimaker Cura
- Integration with PrusaSlicer
- Integration with OrcaSlicer
- Print2Go integration
- OctoPrint plugin

---

# Project Architecture

PhoenixGCode separates the processing engine from every user interface.

```
                   PhoenixGCode Core

        Reader
            │
            ▼
        Parser
            │
            ▼
     Interpreter
            │
            ▼
        Analyzer
            │
            ▼
     Recovery Engine
            │
            ▼
      Public Python API
            │
            ├────────────── Web Frontend (Pyodide)
            ├────────────── Cura Plugin
            ├────────────── PrusaSlicer
            ├────────────── OrcaSlicer
            ├────────────── Print2Go
            └────────────── OctoPrint
```

Every frontend uses exactly the same API.

No interface contains recovery logic.

---

# Failed Print Recovery

The recovery workflow is intentionally simple.

1. Load the original G-code.
2. Analyze the file.
3. Measure the physical height of the failed print.
4. Select the recovery layer suggested by PhoenixGCode.
5. Configure homing strategy.
6. Review extrusion state if necessary.
7. Generate a new recovery G-code.
8. Resume printing.

---

# Recovery Features

PhoenixGCode automatically:

- Preserves print temperatures
- Removes slicer startup movements
- Reconstructs printer state
- Restores extrusion state using G92
- Starts from the desired layer
- Generates a new printable G-code

User-selectable options include:

- No Home
- Home X/Y
- Full Home
- Manual positioning
- Extrusion value adjustment

---

# Web Application

PhoenixGCode includes a browser frontend.

The application runs entirely on the client using Pyodide.

No G-code is uploaded.

No cloud processing is performed.

Your files remain on your computer.

Current development uses:

- Python
- Pyodide
- JavaScript
- HTML
- CSS

The web application is currently tested locally using **VSCode Live Server**.

Future releases are planned for GitHub Pages as a fully static Progressive Web App (PWA).

---

# Supported Firmware

Current focus:

- Marlin

Expected compatibility:

- RepRap Firmware
- Klipper (where compatible with generated G-code)

---

# Supported Slicers

Current testing:

- Ultimaker Cura
- PrusaSlicer
- OrcaSlicer

Since PhoenixGCode operates directly on standard G-code, it is designed to remain slicer-independent whenever possible.

---

# Installation

Python:

```
pip install phoenixgcode
```

Development:

```
git clone https://github.com/<your-user>/PhoenixGCode.git
cd PhoenixGCode
pip install -e .
```

---

# Example

```python
from phoenixgcode import PhoenixGCode

job = PhoenixGCode("cube.gcode")

analysis = job.analyze()

recovery = job.create_recovery(
    z_height=32.40,
    home_mode="xy"
)

recovery.save("cube_recovered.gcode")
```

(The API may evolve before the first stable release.)

---

# Project Status

Current release:

**Beta**

PhoenixGCode is under active development.

The public API may change before version 1.0.

---

# Roadmap

## v0.4

- Failed Print Recovery MVP
- Web Frontend
- Browser execution using Pyodide

## v0.5

- Recovery improvements
- Better recovery assistant
- Additional slicer testing

## v0.6

- Command Line Interface

## v0.7

- Cura Plugin

## v0.8

- Semantic G-code Comparison

## v0.9

- G-code Optimization

## v1.0

- Stable Release

---

# License

PhoenixGCode Community Edition is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

Commercial licensing is available for organizations wishing to integrate PhoenixGCode into proprietary software or commercial products.

See:

- LICENSE
- COMMERCIAL_LICENSE.md

---

# Contributing

Contributions are welcome.

Please read:

- CONTRIBUTING.md

before submitting pull requests.

---

# Acknowledgements

PhoenixGCode has been inspired by prior work from the 3D printing community, including projects related to G-code parsing, visualization and failed print recovery.

Special thanks to the authors of projects such as:

- pygcode
- GcodeParser
- GcodeLens
- reCovery
- 3DPrint UnF**ker
- Gcode Toolkit

Their work helped shape the ideas behind PhoenixGCode.

---

# Philosophy

PhoenixGCode is **not** a slicer.

It is a reusable library dedicated to G-code analysis and failed print recovery.

By keeping the processing engine independent from the user interface, PhoenixGCode can be integrated into multiple desktop, web and embedded applications while maintaining identical behavior across every platform.

---

# Support the Project

If PhoenixGCode saved one of your prints, consider supporting its development.

Future support options will include:

- GitHub Sponsors
- Ko-fi
- Buy Me a Coffee

Your support helps improve the project and keep the Community Edition free and open source.