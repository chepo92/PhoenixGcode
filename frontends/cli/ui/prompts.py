"""
Componente interactivo para solicitar entradas al usuario humano en el Wizard.
"""

import sys
from typing import Dict, Any, Tuple


class CLIPrompts:
    """Solicita parámetros interactivamente si no se entregaron por línea de comandos."""

    @staticmethod
    def ask_measured_z() -> float:
        while True:
            try:
                val = input("\nIngrese la altura Z medida (mm):\n> ").strip()
                return float(val)
            except ValueError:
                print("Por favor ingrese un número válido (ej. 83.42).")

    @staticmethod
    def confirm_generation() -> bool:
        choice = input("¿Generar archivo? [Y/n]: ").strip().lower()
        return choice in ("", "y", "yes")

    @staticmethod
    def prompt_edit_menu(plan_dto: Dict[str, Any], output_path: str) -> Tuple[Dict[str, Any], str]:
        """Permite modificar interactivamente parámetros del plan antes de compilar."""
        state = plan_dto["reconstructed_state"]
        
        while True:
            print("\n¿Desea modificar algún parámetro antes de generar?")
            print(" 1. Cambiar Temperatura Hotend")
            print(" 2. Cambiar Temperatura Cama")
            print(" 3. Cambiar Estrategia de Homing")
            print(" 4. Cambiar Ruta de Archivo Output")
            print(" A. Aceptar Plan y Generar")
            print(" Q. Cancelar")

            ans = input("\nSelección [A/q/1-4]: ").strip().upper()

            if ans in ("", "A"):
                return plan_dto, output_path
            elif ans == "Q":
                print("Operación cancelada por el usuario.")
                sys.exit(0)
            elif ans == "1":
                try:
                    val = float(input(f"Nueva Temp Hotend (ºC) [actual: {state['hotend_temp']}]: "))
                    state["hotend_temp"] = val
                except ValueError:
                    pass
            elif ans == "2":
                try:
                    val = float(input(f"Nueva Temp Cama (ºC) [actual: {state['bed_temp']}]: "))
                    state["bed_temp"] = val
                except ValueError:
                    pass
            elif ans == "3":
                print("Estrategias: 1. HOME_XY | 2. MANUAL_POSITION | 3. HOME_XYZ")
                st_sel = input("Seleccione [1-3]: ").strip()
                st_map = {"1": "HOME_XY", "2": "MANUAL_POSITION", "3": "HOME_XYZ"}
                if st_sel in st_map:
                    plan_dto["strategy"] = st_map[st_sel]
            elif ans == "4":
                new_out = input(f"Nuevo Output File [actual: {output_path}]: ").strip()
                if new_out:
                    output_path = new_out