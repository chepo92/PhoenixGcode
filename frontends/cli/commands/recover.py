"""
Comando 'recover' para PhoenixGCode CLI.
"""

from pathlib import Path
from typing import Optional
import typer

from phoenixgcode.api import PhoenixGCodeAPI
from frontends.cli.commands.base import CLICommand
from frontends.cli.ui.formatter import CLIFormatter
from frontends.cli.ui.prompts import CLIPrompts


class RecoverCommand(CLICommand):

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
            # 1. MODO BATCH (Sin preguntas)
            # ----------------------------------------------------
            if batch:
                if z is None:
                    CLIFormatter.print_error("El parámetro '--z' es obligatorio en modo batch.")
                    raise typer.Exit(code=1)

                base_out = output or file.parent / f"{file.stem}_recovered{file.suffix}"
                output_path, _ = CLIPrompts.resolve_output_path(base_out, interactive=False)
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
            # 2. MODO INTERACTIVO (Wizard)
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
                    # 1. Obtener candidatos
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

                    if selected_cand_idx is None:
                        selected_cand_idx = CLIPrompts.select_candidate(candidates)

                    plan_dto = PhoenixGCodeAPI.plan_recovery(
                        file_path=file,
                        measured_z=current_z,
                        candidate_index=selected_cand_idx,
                        strategy_name=strategy_name,
                    )

                    # 2. Mostrar el Recovery Plan con la ruta propuesta
                    CLIFormatter.print_recovery_plan(plan_dto, str(output_path))

                    # 3. Menú de Edición
                    plan_dto, final_out_str, re_evaluate_z = CLIPrompts.prompt_edit_menu(plan_dto, str(output_path))
                    output_path = Path(final_out_str)
                    strategy_name = plan_dto["strategy"]

                    if "selected_candidate_index" in plan_dto:
                        selected_cand_idx = plan_dto["selected_candidate_index"]

                    if re_evaluate_z:
                        current_z = None
                        selected_cand_idx = None
                        continue

                    # 4. Resolver conflicto de sobrescritura de archivo
                    final_resolved_path, was_prompted = CLIPrompts.resolve_output_path(output_path, interactive=True)

                    # 5. Confirmación final sólo si no se preguntó explícitamente durante resolve_output_path
                    should_generate = was_prompted or CLIPrompts.confirm_generation(final_resolved_path.name)

                    if should_generate:
                        state = plan_dto["reconstructed_state"]
                        final_path = PhoenixGCodeAPI.execute_recovery(
                            input_path=file,
                            output_path=final_resolved_path,
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