"""
Modelos de datos para el Tokenizer de PhoenixGCode.
"""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Tipos léxicos fundamentales de un archivo G-code."""
    COMMAND_LETTER = auto()  # Letras de comando principales: G, M, T
    COMMAND_NUMBER = auto()  # Código numérico de comando: 0, 1, 28, 104, etc.
    PARAM_LETTER = auto()    # Letras de parámetro: X, Y, Z, E, F, S, P, etc.
    PARAM_VALUE = auto()     # Valor asociado al parámetro: 10.5, -2.0, 200
    WHITESPACE = auto()      # Espacios en blanco o tabulaciones
    COMMENT_SYMBOL = auto()  # Caracter delimitador de comentario ';'
    COMMENT_TEXT = auto()    # Texto del comentario posterior al ';'
    UNKNOWN = auto()         # Secuencias no estándar o cadenas sin formato explícito


@dataclass(frozen=True, slots=True)
class Token:
    """
    Representa una unidad léxica individual dentro de una línea de G-code.

    Attributes:
        token_type: Tipo léxico del token.
        value: Valor en texto exacto del token.
        line_number: Número de línea física de procedencia (1-indexed).
        column: Posición base en caracteres dentro de la línea (0-indexed).
    """
    token_type: TokenType
    value: str
    line_number: int
    column: int