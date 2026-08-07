"""
Ensamblador principal de la aplicación CLI Typer.
"""

import typer
from frontends.cli.commands.analyze import AnalyzeCommand
from frontends.cli.commands.inspect import InspectCommand
from frontends.cli.commands.recover import RecoverCommand
from frontends.cli.commands.validate import ValidateCommand

app = typer.Typer(
    name="phoenix",
    help="PhoenixGCode CLI: Herramienta oficial de línea de comandos para recuperar y analizar G-code.",
    add_completion=False,
)

# Registro extensible de comandos inspirados en la interfaz Command
COMMANDS = [
    AnalyzeCommand(),
    InspectCommand(),
    RecoverCommand(),
    ValidateCommand(),
]

for cmd in COMMANDS:
    cmd.register(app)


def main():
    app()


if __name__ == "__main__":
    main()