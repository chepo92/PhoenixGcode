"""
Módulo Tokenizer de PhoenixGCode.

Responsable de convertir texto plano de G-code en una secuencia
ordenada de tokens léxicos sin interpretar su significado.
"""

import re
from typing import Iterator, List, Tuple
from phoenixgcode.tokenizer.token import Token, TokenType


class GCodeTokenizer:
    """
    Tokenizer léxico para G-code compatible con estándares RS-274, Marlin, Klipper y RepRap.

    Preserva el 100% de los elementos originales: orden, número de línea,
    espacios en blanco y comentarios exactos.
    """

    # Expresión regular para tokenización por captura secuencial
    _TOKEN_RE = re.compile(
        r"(?P<WHITESPACE>[ \t]+)|"
        r"(?P<COMMENT>;.*)|"
        r"(?P<WORD>[A-Za-z])|"
        r"(?P<NUMBER>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)|"
        r"(?P<UNKNOWN>[^\sA-Za-z0-9;]+)"
    )

    def tokenize_line(self, line_number: int, line_text: str) -> List[Token]:
        """
        Tokeniza una línea individual de texto.

        Args:
            line_number: Número de línea actual (1-indexed).
            line_text: Cadena de texto de la línea completa.

        Returns:
            Lista ordenada de objetos Token que componen la línea.
        """
        tokens: List[Token] = []
        col = 0
        text_length = len(line_text)

        # Contexto de estado léxico para asociar palabras con sus valores/números
        last_letter: str | None = None

        while col < text_length:
            match = self._TOKEN_RE.match(line_text, col)
            if not match:
                # Fallback por caracter desconocido si el regex no hace match
                char = line_text[col]
                tokens.append(Token(TokenType.UNKNOWN, char, line_number, col))
                col += 1
                continue

            kind = match.lastgroup
            val = match.group(kind)
            start_col = col
            col = match.end()

            if kind == "WHITESPACE":
                tokens.append(Token(TokenType.WHITESPACE, val, line_number, start_col))

            elif kind == "COMMENT":
                # Separa el símbolo ';' del contenido para mantener granularidad si es necesario
                tokens.append(Token(TokenType.COMMENT_SYMBOL, ";", line_number, start_col))
                comment_text = val[1:]
                if comment_text:
                    tokens.append(Token(TokenType.COMMENT_TEXT, comment_text, line_number, start_col + 1))

            elif kind == "WORD":
                letter_upper = val.upper()
                last_letter = letter_upper

                # Diferenciar letra de comando (G, M, T) de letra de parámetro (X, Y, Z, E, S, etc.)
                if letter_upper in {"G", "M", "T"}:
                    tokens.append(Token(TokenType.COMMAND_LETTER, val, line_number, start_col))
                else:
                    tokens.append(Token(TokenType.PARAM_LETTER, val, line_number, start_col))

            elif kind == "NUMBER":
                if last_letter in {"G", "M", "T"}:
                    tokens.append(Token(TokenType.COMMAND_NUMBER, val, line_number, start_col))
                else:
                    tokens.append(Token(TokenType.PARAM_VALUE, val, line_number, start_col))
                last_letter = None

            elif kind == "UNKNOWN":
                tokens.append(Token(TokenType.UNKNOWN, val, line_number, start_col))
                last_letter = None

        return tokens

    def tokenize_stream(self, line_stream: Iterator[Tuple[int, str]]) -> Iterator[List[Token]]:
        """
        Generador que procesa un flujo (stream) de líneas provenientes del Reader.

        Args:
            line_stream: Iterador que entrega (número_de_línea, texto_de_línea).

        Yields:
            Lista de tokens correspondiente a cada línea procesada.
        """
        for line_number, line_text in line_stream:
            yield self.tokenize_line(line_number, line_text)