"""
Módulo de Interfaz de Línea de Comandos (CLI) de PhoenixGCode.

Proporciona comandos interactivos para ejecutar planes de recuperación (Recovery)
bajo el principio de Automatización Supervisada: Phoenix analiza e infiere,
pero el usuario siempre revisa y decide antes de escribir a disco.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from phoenixgcode.reader.reader import GCodeReader
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.analyzer.analyzer import GCodeAnalyzer
from phoenixgcode.transformer.recovery.planner import RecoveryPlanner
from phoenixgcode.transformer.recovery.builder import RecoveryBuilder
from phoenixgcode.writer.writer import GCodeWriter
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType


def print_banner() -> None:
    """Imprime el encabezado oficial de PhoenixGCode en la consola."""
    banner = r"""
===========================================================
  ___  _                     _       ___  ____            _ 
 / _ \| |__   ___   ___ _ __(_)_  __/ _ \/ ___|___   __| |___
| |_) | '_ \ / _ \ / _ \ '_ \ \ \/ / | | | |   / _ \ / _` / _ \
|  __/| | | | (_) |  __/ | | | >  <| |_| | |__| (_) | (_|  __/
|_|   |_| |_|\___/ \___|_| |_|_/_/\_\\___/\____\___/ \__,_\___|

        "A universal G-code analysis and failed print recovery library."
===========================================================
"""
    print(banner)


def parse_args() -> argparse.Namespace:
    """Configura y analiza los argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="phoenix",
        description="PhoenixGCode: Biblioteca y herramienta CLI para recuperar y transformar archivos G-code.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Subcomando: recover
    recover_parser = subparsers.add_parser(
        "recover",
        help="Planifica y genera un archivo de recuperación para una impresión interrumpida.",
    )
    recover_parser.add_argument(
        "file",
        type=str,
        help="Ruta al archivo .gcode original interrumpido.",
    )
    recover_parser.add_argument(
        "-z", "--z-height",
        type=float,
        default=None,
        help="Altura Z física medida en la pieza (en mm). Si omitida, se solicitará de forma interactiva.",
    )
    recover_parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Ruta del archivo de salida. Por defecto: '<nombre>_Recovery.gcode'.",
    )
    recover_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Genera el archivo directamente usando la información autodetectada sin menú interactivo.",
    )

    return parser.parse_args()


def prompt_user_settings(settings: RecoverySettings, default_z: float) -> RecoverySettings:
    """
    Despliega el menú interactivo para que el usuario pueda modificar 
    cualquier parámetro inferido por PhoenixGCode.
    """
    print("\n--- PARAMETROS DETECTADOS / CONFIGURACION DE RECUPERACION ---")
    print(f" 1. Altura Z Medida:        {settings.measured_z:.3f} mm")
    print(f" 2. Estrategia Homing:      {settings.strategy.name}")
    print(f" 3. Hotend Temp Override:   {settings.override_hotend_temp if settings.override_hotend_temp is not None else '[Usar valor autodetectado]'}")
    print(f" 4. Cama Temp Override:     {settings.override_bed_temp if settings.override_bed_temp is not None else '[Usar valor autodetectado]'}")
    print(f" 5. Ventilador Override:    {settings.override_fan_speed if settings.override_fan_speed is not None else '[Usar valor autodetectado]'}")
    print(f" 6. Distancia Z-Hop:        {settings.z_hop_distance:.1f} mm")
    print(" -----------------------------------------------------------")
    print(" A. Aceptar Plan y Generar Archivo")
    print(" Q. Cancelar")

    while True:
        choice = input("\nSeleccione una opción a modificar [A/Q/1-6]: ").strip().upper()

        if choice == "A" or choice == "":
            return settings
        elif choice == "Q":
            print("\nOperación cancelada por el usuario.")
            sys.exit(0)
        elif choice == "1":
            try:
                val = float(input(f"Ingrese nueva Altura Z (actual: {settings.measured_z:.3f} mm): "))
                settings.measured_z = val
            except ValueError:
                print("Valor numérico inválido.")
        elif choice == "2":
            print("\nEstrategias disponibles:")
            print("  1. HOME_XY (Re-home solo ejes X e Y - Recomendado)")
            print("  2. MANUAL_POSITION (Fijar coordenadas actuales con G92)")
            print("  3. HOME_XYZ (Re-home completo XYZ)")
            print("  4. CUSTOM_SCRIPT (Macro personalizada)")
            strat_choice = input("Seleccione estrategia [1-4]: ").strip()
            strat_map = {
                "1": RecoveryStrategyType.HOME_XY,
                "2": RecoveryStrategyType.MANUAL_POSITION,
                "3": RecoveryStrategyType.HOME_XYZ,
                "4": RecoveryStrategyType.CUSTOM_SCRIPT,
            }
            if strat_choice in strat_map:
                settings.strategy = strat_map[strat_choice]
            else:
                print("Opción no válida.")
        elif choice == "3":
            val_str = input("Temperatura Hotend (ºC) [Presione Enter para autodetectar]: ").strip()
            settings.override_hotend_temp = float(val_str) if val_str else None
        elif choice == "4":
            val_str = input("Temperatura Cama (ºC) [Presione Enter para autodetectar]: ").strip()
            settings.override_bed_temp = float(val_str) if val_str else None
        elif choice == "5":
            val_str = input("Velocidad Ventilador (0-255) [Presione Enter para autodetectar]: ").strip()
            settings.override_fan_speed = float(val_str) if val_str else None
        elif choice == "6":
            try:
                val = float(input(f"Distancia Z-hop clearance (mm) (actual: {settings.z_hop_distance:.1f}): "))
                settings.z_hop_distance = val
            except ValueError:
                print("Valor numérico inválido.")

        # Re-imprimir menú actualizado tras cambio
        return prompt_user_settings(settings, default_z)


def run_recover(args: argparse.Namespace) -> None:
    """Ejecuta la canalización de recuperación completa."""
    input_path = Path(args.file)

    if not input_path.exists():
        print(f"Error: El archivo '{input_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    # Solicitar altura Z si no fue provista por argumento CLI
    measured_z = args.z_height
    if measured_z is None:
        try:
            val_str = input("Ingrese la altura Z medida en la pieza (mm): ").strip()
            measured_z = float(val_str)
        except ValueError:
            print("Error: Debe ingresar una altura Z numérica válida.", file=sys.stderr)
            sys.exit(1)

    print(f"\n[1/5] Leyendo y parseando '{input_path.name}'...")
    reader = GCodeReader(input_path)
    tokenizer = GCodeTokenizer()
    parser = GCodeParser()

    token_stream = tokenizer.tokenize_stream(reader.read_lines())
    document = parser.parse_stream(token_stream)
    print(f"      -> {len(document)} líneas/comandos parseados.")

    print("[2/5] Reconstruyendo estado virtual (Interpreter & Analyzer)...")
    interpreter = GCodeInterpreter()
    timeline = interpreter.interpret(document)

    analyzer = GCodeAnalyzer()
    analysis = analyzer.analyze(document, timeline)

    print(f"      -> {analysis.layer_index.total_layers} capas detectadas. Altura máxima: {analysis.max_z_height:.3f} mm")

    print(f"[3/5] Identificando punto de corte a Z = {measured_z:.3f} mm...")
    planner = RecoveryPlanner()
    initial_settings = RecoverySettings(measured_z=measured_z)

    candidates = planner.find_candidates(document, timeline, analysis, initial_settings)

    if not candidates:
        print(f"Error: No se encontró ningún comando válido cercano a Z = {measured_z:.3f} mm.", file=sys.stderr)
        sys.exit(1)

    top_candidate = candidates[0]
    print(f"      -> Candidato seleccionado: Línea {top_candidate.line_number} (Capa #{top_candidate.layer_index}, Confianza: {top_candidate.confidence_score*100:.1f}%)")

    # Construir plan preliminar
    plan = planner.create_plan(top_candidate, initial_settings)

    # Interacción con el usuario (Automatización Supervisada)
    if not args.non_interactive:
        final_settings = prompt_user_settings(initial_settings, measured_z)
        # Regenerar el plan con la configuración confirmada por el usuario
        plan = planner.create_plan(top_candidate, final_settings)
    else:
        final_settings = initial_settings

    print("\n[4/5] Ensamblando nuevo Document de recuperación...")
    builder = RecoveryBuilder()
    recovery_document = builder.build_document(document, plan, final_settings)

    # Determinar ruta de salida
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_Recovery.gcode"

    print(f"[5/5] Escribiendo archivo en '{output_path.name}'...")
    writer = GCodeWriter()
    writer.write_to_file(recovery_document, output_path)

    print(f"\n✔ ¡Proceso finalizado con éxito! Archivo de recuperación generado: {output_path.resolve()}")


def main() -> None:
    """Punto de entrada principal para el comando de terminal 'phoenix'."""
    print_banner()
    args = parse_args()

    if args.command == "recover":
        run_recover(args)
    else:
        print("Uso: phoenix recover <archivo.gcode> [-z ALTURA_Z]")
        sys.exit(0)


if __name__ == "__main__":
    main()