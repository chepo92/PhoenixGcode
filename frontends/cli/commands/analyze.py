"""
Comando 'analyze' para PhoenixGCode CLI.
"""

from pathlib import Path
import typer
from phoenixgcode.api import PhoenixGCodeAPI
from frontends.cli.commands.base import CLICommand
from frontends.cli.ui.formatter import CLIFormatter


class AnalyzeCommand(CLICommand):

    def register(self, app: typer.Typer) -> None:
        @app.command(name="analyze", help="Analiza e indexa un archivo G-code mostrando sus métricas.")
        def analyze(file: Path = typer.Argument(..., help="Archivo G-code a analizar.")):
            if not file.exists():
                CLIFormatter.print_error(f"El archivo '{file}' no existe.")
                raise typer.Exit(code=1)

            try:
                res = PhoenixGCodeAPI.analyze_file(file)
                CLIFormatter.print_step(f"Archivo leído: {res['source_file']}")
                CLIFormatter.print_step(f"{res['total_lines']} líneas / comandos parseados")
                CLIFormatter.print_step(f"{res['total_layers']} capas detectadas")
                CLIFormatter.print_step(f"Altura máxima Z: {res['max_z_height']:.3f} mm")
                CLIFormatter.print_step("Temperaturas y snapshots indexados")
            except Exception as e:
                CLIFormatter.print_error(str(e))
                raise typer.Exit(code=1)