"""
Módulo Writer de PhoenixGCode.

Responsable exclusivamente de la conversión de un objeto Document de regreso a 
texto plano de G-code o de su escritura en disco, preservando el 100% del 
formato original, espacios y comentarios.
"""

from pathlib import Path
from typing import Union, Iterator, Optional
from phoenixgcode.model.document import Document
from phoenixgcode.model.command import Command


class GCodeWriter:
    """
    Escritor y formateador de objetos Document a G-code.

    Garantiza la máxima fidelidad de representación respecto al documento original.
    """

    def write_stream(self, document: Document) -> Iterator[str]:
        """
        Generador que emite cada comando formateado como una línea de texto (streaming).

        Args:
            document: El Document con la secuencia de comandos.

        Yields:
            Cadena de texto correspondiente a cada línea G-code.
        """
        for cmd in document:
            yield self.format_command(cmd)

    def write_to_string(self, document: Document, line_ending: str = "\n") -> str:
        """
        Convierte el Document completo en una sola cadena de texto.

        Args:
            document: El Document a formatear.
            line_ending: Salto de línea deseado (predeterminado '\\n').

        Returns:
            Texto completo del archivo G-code.
        """
        return line_ending.join(self.write_stream(document))

    def write_to_file(
        self,
        document: Document,
        output_path: Union[str, Path],
        encoding: str = "utf-8",
        line_ending: str = "\n",
    ) -> Path:
        """
        Escribe el Document en un archivo físico en disco.

        Args:
            document: El Document a escribir.
            output_path: Ruta del archivo de destino (.gcode).
            encoding: Codificación de texto deseada (default 'utf-8').
            line_ending: Salto de línea a utilizar.

        Returns:
            Path apuntando al archivo escrito.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding=encoding, newline="") as f:
            for line in self.write_stream(document):
                f.write(line + line_ending)

        return path

    def format_command(self, command: Command) -> str:
        """
        Formatea una instancia individual de Command a texto plano.

        Si el comando posee su raw_text original, se utiliza directamente para 
        preservar el formato exacto. De lo contrario, reconstruye la línea sintácticamente.

        Args:
            command: Instancia de Command a formatear.

        Returns:
            Cadena de texto equivalente en G-code.
        """
        # 1. Utilizar texto bruto si está presente (preserva el formato exacto original)
        if command.raw_text:
            return command.raw_text

        # 2. Reconstrucción sintáctica en caso de comandos creados dinámicamente
        parts = []

        if command.code:
            parts.append(command.code)

        for param, val in command.parameters.items():
            # Formatear como entero si no tiene decimales significativos
            if isinstance(val, float) and val.is_integer():
                parts.append(f"{param}{int(val)}")
            else:
                parts.append(f"{param}{val}")

        line_str = " ".join(parts)

        if command.comment:
            if line_str:
                line_str += f" ; {command.comment.lstrip('; ')}"
            else:
                line_str = f"; {command.comment.lstrip('; ')}"

        return line_str