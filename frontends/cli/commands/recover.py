"""
Comando 'recover' para PhoenixGCode CLI.
"""

import sys
from pathlib import Path
from typing import Optional
import typer

from phoenixgcode.api import PhoenixGCodeAPI
from frontends.cli.commands.base import CLICommand
from frontends.cli.ui.formatter import CLIFormatter
from frontends.cli.ui.prompts import CLIPrompts


class RecoverCommand(CLICommand):
    """Comando de recuperación que implementa la interfaz CLICommand."""

    def register(self, app: typer.Typer) -> None:
        @app.command(name="recover", help="Planifica y genera un archivo Recovery.gcode.")
        def recover(
            file: Path = typer.Argument(..., help="Archivo G-code original interrumpido."),
            z: Optional[float] = typer.Option(None, "--z", help="Altura Z medida (mm)."),
            candidate: Optional[int] = typer.Option(None, "--candidate", help="Índice del candidato a utilizar."),
            home: str = typer.Option("xy", "--home", help="Estrategia Homing (xy, xyz, manual)."),
            output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta del archivo de salida."),
            batch: bool = typer.Option(False, "--batch", help="Ejecutar en modo Batch no interactivo."),
        ):
            if not file.exists():
                CLIFormatter.print_error(f"El archivo '{file}' no existe.")
                raise typer.Exit(code=1)

            home_map = {"xy": "HOME_XY", "xyz": "HOME_XYZ", "manual": "MANUAL_POSITION"}
            strategy_name = home_map.get(home.lower(), "HOME_XY")

            # ----------------------------------------------------
            # 1. MODO BATCH (Estricto, sin preguntas)
            # ----------------------------------------------------
            if batch:
                if z is None:
                    CLIFormatter.print_error("El parámetro '--z' es obligatorio en modo batch.")
                    raise typer.Exit(code=1)

                output_path = output or file.parent / f"{file.stem}_recovered{file.suffix}"
                cand_idx = candidate if candidate is not None else 0

                try:
                    res = PhoenixGCodeAPI.execute_recovery(
                        input_path=file,
                        output_path=output_path,
                        measured_z=z,
                        candidate_index=cand_idx,
                        strategy_name=strategy_name,
                    )
                    CLIFormatter.print_step(f"Archivo de recuperación generado exitosamente en: {res}")
                    return
                except Exception as e:
                    CLIFormatter.print_error(str(e))
                    raise typer.Exit(code=1)

            # ----------------------------------------------------
            # 2. MODO INTERACTIVO (Asistido / Wizard)
            # ----------------------------------------------------
            CLIFormatter.print_banner()
            CLIFormatter.print_step(f"Archivo cargado: {file.name}")
            CLIFormatter.print_step("Analizando G-code...")
            CLIFormatter.print_step("Estado reconstruido")

            current_z = z
            selected_cand_idx = candidate
            output_path = output or file.parent / f"{file.stem}_recovered{file.suffix}"

            while True:
                if current_z is None:
                    current_z = CLIPrompts.ask_measured_z()

                try:
                    # 1. Obtener propuesta y lista de candidatos
                    plan_dto = PhoenixGCodeAPI.plan_recovery(
                        file_path=file,
                        measured_z=current_z,
                        candidate_index=0,
                        strategy_name=strategy_name,
                    )

                    candidates = plan_dto.get("candidates", [])
                    if not candidates:
                        CLIFormatter.print_error(f"No se encontraron candidatos para Z = {current_z:.3f}mm")
                        current_z = None
                        continue

                    # 2. Desplegar la lista de candidatos si no fue fijado un --candidate específico
                    if selected_cand_idx is None:
                        selected_cand_idx = CLIPrompts.select_candidate(candidates)

                    # 3. Recalcular el plan definitivo con la opción elegida
                    plan_dto = PhoenixGCodeAPI.plan_recovery(
                        file_path=file,
                        measured_z=current_z,
                        candidate_index=selected_cand_idx,
                        strategy_name=strategy_name,
                    )

                    # 4. Mostrar el Recovery Plan completo
                    CLIFormatter.print_recovery_plan(plan_dto, str(output_path))

                    # 5. Desplegar Menú de Edición
                    plan_dto, final_out_str, re_evaluate_z = CLIPrompts.prompt_edit_menu(plan_dto, str(output_path))
                    output_path = Path(final_out_str)
                    strategy_name = plan_dto["strategy"]

                    # Permitir re-seleccionar candidato en el menú interactivo opción 2
                    if "selected_candidate_index" in plan_dto:
                        selected_cand_idx = plan_dto["selected_candidate_index"]

                    if re_evaluate_z:
                        current_z = None
                        selected_cand_idx = None
                        continue

                    # 6. Confirmación final de generación
                    if CLIPrompts.confirm_generation():
                        state = plan_dto["reconstructed_state"]
                        final_path = PhoenixGCodeAPI.execute_recovery(
                            input_path=file,
                            output_path=output_path,
                            measured_z=current_z,
                            candidate_index=selected_cand_idx,
                            strategy_name=strategy_name,
                            override_hotend_temp=state["hotend_temp"],
                            override_bed_temp=state["bed_temp"],
                        )
                        CLIFormatter.print_step(f"¡Proceso finalizado! Archivo generado en: {final_path}")
                        break
                    else:
                        print("Generación cancelada.")
                        break

                except Exception as e:
                    CLIFormatter.print_error(str(e))
                    current_z = None
                    selected_cand_idx = None