"""
Componente interactivo para solicitar entradas al usuario humano en el Wizard.
"""

import sys
from typing import Dict, Any, Tuple, List


class CLIPrompts:
    """Solicita parámetros interactivamente si no se entregaron por línea de comandos."""

    @staticmethod
    def ask_measured_z() -> float:
        """Solicita la altura Z medida físicamente."""
        while True:
            try:
                val = input("\nIngrese la altura Z medida en la pieza (mm):\n> ").strip()
                return float(val)
            except ValueError:
                print("❌ Por favor ingrese un número válido (ej. 83.42).")

    @staticmethod
    def select_candidate(candidates: List[Dict[str, Any]]) -> int:
        """
        Muestra la lista de candidatos encontrados para la altura Z
        y permite al usuario seleccionar uno o mantener el recomendado.
        """
        print("\n--- CANDIDATOS ENCONTRADOS ---")
        for cand in candidates:
            idx = cand["index"]
            is_rec = " (Recomendado)" if idx == 0 else ""
            conf = cand["confidence_score"] * 100.0
            print(f" [{idx}] Línea {cand['line_number']} | Capa #{cand['layer_index']} | Z: {cand['target_z']:.3f}mm | Confianza: {conf:.1f}%{is_rec}")
        print(" ----------------------------")

        while True:
            max_idx = max(0, len(candidates) - 1)
            prompt_str = "Seleccione el candidato a usar [0]" if len(candidates) == 1 else f"Seleccione el candidato a usar [0-{max_idx}] (Enter para [0])"
            choice = input(f"{prompt_str}: ").strip()
            if choice == "":
                return 0
            if choice.isdigit():
                val = int(choice)
                if 0 <= val < len(candidates):
                    return val
            print("❌ Selección fuera de rango.")

    @staticmethod
    def confirm_generation() -> bool:
        """Confirma la generación del archivo final."""
        choice = input("\n¿Generar archivo Recovery.gcode? [Y/n]: ").strip().lower()
        return choice in ("", "y", "yes")

    @staticmethod
    def prompt_edit_menu(plan_dto: Dict[str, Any], output_path: str) -> Tuple[Dict[str, Any], str, bool]:
        """
        Permite modificar interactivamente parámetros del plan antes de compilar.

        Returns:
            Tupla de (plan_dto, output_path, re_evaluate_z_flag)
            Si re_evaluate_z_flag es True, la CLI volverá a solicitar Z.
        """
        state = plan_dto["reconstructed_state"]
        cand = plan_dto["candidate"]
        
        while True:
            print("\n--- MENU DE EDICION DEL RECOVERY PLAN ---")
            print(f" 1. Cambiar Altura Z Medida     (actual: {cand['target_z']:.3f} mm)")
            print(f" 2. Cambiar Candidato de Capa   (actual: Línea {cand['line_number']}, Capa #{cand['layer_index']})")
            print(f" 3. Cambiar Temp Hotend          (actual: {state['hotend_temp']:.0f}°C)")
            print(f" 4. Cambiar Temp Cama            (actual: {state['bed_temp']:.0f}°C)")
            print(f" 5. Cambiar Estrategia Homing    (actual: {plan_dto['strategy']})")
            print(f" 6. Cambiar Ruta de Salida       (actual: {output_path})")
            print(" ----------------------------------------")
            print(" A. Aceptar Plan y Continuar")
            print(" Q. Cancelar")

            ans = input("\nSelección [A/q/1-6]: ").strip().upper()

            if ans in ("", "A"):
                return plan_dto, output_path, False
            elif ans == "Q":
                print("\nOperación cancelada por el usuario.")
                sys.exit(0)
            elif ans == "1":
                return plan_dto, output_path, True
            elif ans == "2":
                candidates = plan_dto.get("candidates", [])
                if candidates:
                    new_idx = CLIPrompts.select_candidate(candidates)
                    plan_dto["selected_candidate_index"] = new_idx
                    return plan_dto, output_path, False
            elif ans == "3":
                try:
                    val = float(input(f"Nueva Temp Hotend (ºC) [actual: {state['hotend_temp']}]: "))
                    state["hotend_temp"] = val
                except ValueError:
                    pass
            elif ans == "4":
                try:
                    val = float(input(f"Nueva Temp Cama (ºC) [actual: {state['bed_temp']}]: "))
                    state["bed_temp"] = val
                except ValueError:
                    pass
            elif ans == "5":
                print("\nEstrategias: 1. HOME_XY | 2. MANUAL_POSITION | 3. HOME_XYZ")
                st_sel = input("Seleccione [1-3]: ").strip()
                st_map = {"1": "HOME_XY", "2": "MANUAL_POSITION", "3": "HOME_XYZ"}
                if st_sel in st_map:
                    plan_dto["strategy"] = st_map[st_sel]
            elif ans == "6":
                new_out = input(f"Nuevo Output File [actual: {output_path}]: ").strip()
                if new_out:
                    output_path = new_out