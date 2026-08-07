"""
Componente interactivo para solicitar entradas al usuario humano en el Wizard.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List


class CLIPrompts:

    @staticmethod
    def resolve_output_path(base_path: Path, interactive: bool = True) -> Tuple[Path, bool]:
        """
        Garantiza que el archivo de salida no sobrescriba archivos existentes sin confirmación.
        
        Returns:
            Tupla (path_resuelto, fue_confirmado_interactivamente)
        """
        if not base_path.exists():
            return base_path, False

        if interactive:
            print(f"\n⚠️  El archivo '{base_path.name}' ya existe.")
            choice = input("¿Desea sobrescribirlo? [y/N]: ").strip().lower()
            if choice in ("y", "yes"):
                return base_path, True

        # Si no se sobrescribe o en modo batch, generar nombre incremental: _001, _002, etc.
        stem = base_path.stem
        ext = base_path.suffix
        parent = base_path.parent
        counter = 1

        while True:
            new_path = parent / f"{stem}_{counter:03d}{ext}"
            if not new_path.exists():
                # En este caso se le asignó un nombre nuevo seguro, por lo que no requiere re-confirmación de sobrescritura
                return new_path, True
            counter += 1

    @staticmethod
    def ask_measured_z() -> float:
        while True:
            try:
                val = input("\nIngrese la altura Z medida en la pieza (mm):\n> ").strip()
                return float(val)
            except ValueError:
                print("❌ Por favor ingrese un número válido (ej. 83.42).")

    @staticmethod
    def select_candidate(candidates: List[Dict[str, Any]]) -> int:
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
    def confirm_generation(target_filename: str) -> bool:
        """Confirma la generación mostrando explícitamente el archivo a crear."""
        choice = input(f"\n¿Generar archivo '{target_filename}'? [Y/n]: ").strip().lower()
        return choice in ("", "y", "yes")

    @staticmethod
    def prompt_edit_menu(plan_dto: Dict[str, Any], output_path: str) -> Tuple[Dict[str, Any], str, bool]:
        state = plan_dto["reconstructed_state"]
        cand = plan_dto["candidate"]
        
        while True:
            print("\n--- MENU DE EDICION DEL RECOVERY PLAN ---")
            print(f" 1. Cambiar Altura Z Medida       (actual: {cand['target_z']:.3f} mm)")
            print(f" 2. Cambiar Candidato de Capa     (actual: Línea {cand['line_number']}, Capa #{cand['layer_index']})")
            print(f" 3. Cambiar Temp Hotend            (actual: {state['hotend_temp']:.0f}°C)")
            print(f" 4. Cambiar Temp Cama              (actual: {state['bed_temp']:.0f}°C)")
            print(f" 5. Cambiar Estrategia de Homing   (actual: {plan_dto['strategy']})")
            print(f" 6. Cambiar Ruta de Salida         (actual: {output_path})")
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