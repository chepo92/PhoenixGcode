"""
Módulo Reader de PhoenixGCode.

Responsable exclusivamente de la lectura de archivos G-code desde disco,
detección de codificación (encoding) y emisión de líneas mediante streaming.
"""

from pathlib import Path
from typing import Iterator, Union, Tuple, Optional
import chardet


class GCodeReader:
    """
    Lector optimizado para archivos G-code.

    Lee el archivo en modo streaming línea por línea para evitar consumir
    memoria excesiva con archivos de gran tamaño (> 1 GB).
    """

    def __init__(self, file_path: Union[str, Path], buffer_size: int = 65536) -> None:
        """
        Inicializa el GCodeReader.

        Args:
            file_path: Ruta al archivo .gcode a leer.
            buffer_size: Tamañoo del buffer en bytes usado para detectar el encoding.
        """
        self.file_path = Path(file_path)
        self.buffer_size = buffer_size

        if not self.file_path.exists():
            raise FileNotFoundError(f"El archivo no existe: {self.file_path}")
        if not self.file_path.is_file():
            raise IsADirectoryError(f"La ruta proporcionada es un directorio: {self.file_path}")

    def detect_encoding(self) -> str:
        """
        Detecta la codificación de texto del archivo sin cargarlo completo en memoria.

        Primero verifica encodings comunes y firmas BOM (UTF-8, UTF-16).
        Si no coinciden, utiliza un muestreo limitado con `chardet`.

        Returns:
            Nombre del encoding detectado (ej. 'utf-8', 'utf-8-sig', 'latin-1').
        """
        with open(self.file_path, "rb") as f:
            raw_sample = f.read(self.buffer_size)

        if not raw_sample:
            return "utf-8"

        # Detección rápida de Byte Order Mark (BOM)
        if raw_sample.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if raw_sample.startswith((b"\xff\xfe", b"\xfe\xff")):
            return "utf-16"

        # Intento primario con UTF-8 estricto
        try:
            raw_sample.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass

        # Inferencia mediante muestreo con chardet
        detected = chardet.detect(raw_sample)
        encoding = detected.get("encoding")

        if encoding:
            return encoding.lower()

        # Fallback seguro para archivos de texto donde ningún byte falla
        return "latin-1"

    def read_lines(self, encoding: Optional[str] = None) -> Iterator[Tuple[int, str]]:
        """
        Generador que lee el archivo línea por línea (streaming).

        Args:
            encoding: Opcional. Si no se provee, se detectará automáticamente.

        Yields:
            Tupla de (número_de_línea, texto_de_la_línea)
            donde número_de_línea es 1-indexed y el texto mantiene sus caracteres
            originales (excluyendo el salto de línea al final).
        """
        active_encoding = encoding or self.detect_encoding()

        with open(self.file_path, "r", encoding=active_encoding, errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                yield line_number, line.rstrip("\r\n")