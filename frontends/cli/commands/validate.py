"""
Comando 'validate' para PhoenixGCode CLI.
"""

from pathlib import Path
import typer
from phoenixgcode.api import PhoenixGCodeAPI
from frontends.cli.commands.base import CLICommand
from frontends.cli.ui.formatter import CLIFormatter


class ValidateCommand(CLICommand):

    def register(self, app: typer.Typer) -> None:
        @app.command(name="validate", help="Valida la sintaxis y legibilidad de un archivo G-code.")
        def validate(file: Path = typer.Argument(..., help="Archivo G-code a me validar.")):
            if not file.exists():
                CLIFormatter.print_error(f"El archivo '{file}' no existe.")
                raise typer.Exit(code=1)

            res = PhoenixGCodeAPI.validate_file(file)
            if res["valid"]:
                CLIFormatter.print_step(f"Sintaxis válida ({res['encoding']})")
                CLIFormatter.print_step(f"{res['total_commands']} comandos parseados exitosamente sin errores.")
            else:
                CLIFormatter.print_error(f"Archivo inválido: {res['error']}")
                raise typer.Exit(code=1)