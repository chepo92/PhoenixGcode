"""
Interfaz base y contrato para todos los comandos CLI.
"""

from abc import ABC, abstractmethod
import typer


class CLICommand(ABC):
    """Contrato abstracto para los comandos de la CLI."""

    @abstractmethod
    def register(self, app: typer.Typer) -> None:
        """Registra el subcomando en la aplicación Typer."""
        pass