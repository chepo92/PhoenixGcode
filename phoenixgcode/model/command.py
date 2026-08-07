from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, Tuple, Any, List


class CommandType(Enum):
    """Categorías principales de líneas en un archivo G-code."""
    MOTION = auto()       # G0, G1, G2, G3, etc.
    SETTING = auto()      # G90, G91, M82, M83, G21, G20, etc.
    TEMPERATURE = auto()  # M104, M109, M140, M190, etc.
    FAN = auto()          # M106, M107
    HOME = auto()         # G28
    COMMENT = auto()      # Líneas vacías o de puro comentario
    OTHER = auto()        # M500, M117, etc.


@dataclass(frozen=True, slots=True)
class Command:
    """
    Representa una línea o comando base dentro del archivo G-code.
    
    Attributes:
        line_number: Número de línea física en el archivo original (1-indexed).
        raw_text: Cadena de texto exacta leída del archivo.
        code: Identificador principal en mayúsculas (ej. 'G1', 'M104', 'G28').
        parameters: Diccionario de letras y sus valores flotantes (ej. {'X': 10.5, 'Y': 20.0}).
        comment: Texto del comentario adjunto al final de la línea, si existe.
    """
    line_number: int
    raw_text: str
    code: Optional[str] = None
    parameters: Dict[str, float] = field(default_factory=dict)
    comment: Optional[str] = None

    @property
    def command_type(self) -> CommandType:
        if self.code is None:
            return CommandType.COMMENT
        if self.code in {"G0", "G1", "G2", "G3", "G5"}:
            return CommandType.MOTION
        if self.code in {"M104", "M109", "M140", "M190"}:
            return CommandType.TEMPERATURE
        if self.code in {"M106", "M107"}:
            return CommandType.FAN
        if self.code == "G28":
            return CommandType.HOME
        if self.code in {"G90", "G91", "M82", "M83", "G20", "G21", "G92"}:
            return CommandType.SETTING
        return CommandType.OTHER


@dataclass(frozen=True, slots=True)
class MoveCommand(Command):
    """
    Comando especializado para movimientos de ejes (G0, G1, G2, G3).
    
    Attributes:
        x: Posición o desplazamiento objetivo en eje X.
        y: Posición o desplazamiento objetivo en eje Y.
        z: Posición o desplazamiento objetivo en eje Z.
        e: Longitud de extrusión o avance de filamento.
        f: Velocidad de avance (Feedrate) especificada en la línea.
    """
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    e: Optional[float] = None
    f: Optional[float] = None


@dataclass(frozen=True, slots=True)
class TemperatureCommand(Command):
    """
    Comando especializado para control térmico (M104, M109, M140, M190).
    
    Attributes:
        target_temperature: Temperatura objetivo solicitada en grados Celsius (S o R).
        tool_index: Índice del extrusor/herramienta objetivo (T).
        is_bed: True si el comando aplica a la cama caliente, False si es Hotend/Extrusor.
        wait_for_heating: True si el comando detiene la ejecución hasta alcanzar la temp (M109/M190).
    """
    target_temperature: Optional[float] = None
    tool_index: int = 0
    is_bed: bool = False
    wait_for_heating: bool = False


@dataclass(frozen=True, slots=True)
class CommentCommand(Command):
    """
    Comando que representa una línea exclusiva de comentarios o líneas en blanco.
    
    Attributes:
        clean_text: Texto del comentario excluyendo el caracter de inicio ';'.
    """
    clean_text: str = ""