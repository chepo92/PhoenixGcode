"""
Comando 'inspect' para PhoenixGCode CLI.
"""

from pathlib import Path
import typer
from phoenixgcode.api import PhoenixGCodeAPI
from frontends.cli.commands.base import CLICommand
from frontends.cli.ui.formatter import CLIFormatter


class InspectCommand(CLICommand):

    def register(self, app: typer.Typer) -> None:
        @app.command(name="inspect", help="Inspecciona candidatos de recuperación para una altura Z dada.")
        def inspect(
            file: Path = typer.Argument(..., help="Archivo G-code a inspeccionar."),
            z: float = typer.Option(..., "--z", help="Altura Z objetivo (mm)."),
        ):
            if not file.exists():
                CLIFormatter.print_error(f"El archivo '{file}' no existe.")
                raise typer.Exit(code=1)

            try:
                plan_dto = PhoenixGCodeAPI.plan_recovery(file_path=file, measured_z=z)
                print(f"\nCandidatos encontrados para Z = {z:.3f} mm:")
                for cand in plan_dto["candidates"]:
                    print(f"  [#{cand['index']}] Línea: {cand['line_number']} | Layer #{cand['layer_index']} | Confidence: {cand['confidence_score']*100:.1f}%")
            except Exception as e:
                CLIFormatter.print_error(str(e))
                raise typer.Exit(code=1)