"""
Módulo Parser de PhoenixGCode.

Responsable de convertir listas de tokens en objetos Command y sus subclases
(MoveCommand, TemperatureCommand, CommentCommand), preservando parámetros y comentarios
sin interpretar su significado semántico.
"""

from typing import List, Iterator, Optional, Dict
from phoenixgcode.tokenizer.token import Token, TokenType
from phoenixgcode.model.command import (
    Command,
    MoveCommand,
    TemperatureCommand,
    CommentCommand,
)
from phoenixgcode.model.document import Document


class GCodeParser:
    """
    Parser sintáctico de G-code.

    Transforma secuencias de tokens en instancias concretas de Command.
    Es agnóstico al orden de los parámetros en la línea.
    """

    def parse_line_tokens(self, tokens: List[Token]) -> Command:
        """
        Convierte la lista de tokens de una línea individual en un objeto Command.

        Args:
            tokens: Lista de tokens de una misma línea física.

        Returns:
            Instancia de Command (o subclases MoveCommand, TemperatureCommand, CommentCommand).
        """
        if not tokens:
            return CommentCommand(line_number=0, raw_text="", clean_text="")

        line_number = tokens[0].line_number
        raw_text = "".join(t.value for t in tokens)

        command_code: Optional[str] = None
        parameters: Dict[str, float] = {}
        comment_text: Optional[str] = None

        idx = 0
        num_tokens = len(tokens)

        while idx < num_tokens:
            token = tokens[idx]

            if token.token_type == TokenType.COMMAND_LETTER:
                cmd_letter = token.value.upper()
                
                # Si aún NO se ha establecido el código principal de la línea:
                if command_code is None:
                    if idx + 1 < num_tokens and tokens[idx + 1].token_type == TokenType.COMMAND_NUMBER:
                        command_code = f"{cmd_letter}{tokens[idx + 1].value}"
                        idx += 1
                    else:
                        command_code = cmd_letter
                else:
                    # Si YA existe un código de comando principal (ej. M109), 
                    # tratamos cualquier letra subsecuente (ej. T0) como un parámetro.
                    if idx + 1 < num_tokens and tokens[idx + 1].token_type == TokenType.COMMAND_NUMBER:
                        try:
                            parameters[cmd_letter] = float(tokens[idx + 1].value)
                        except ValueError:
                            pass
                        idx += 1

            elif token.token_type == TokenType.PARAM_LETTER:
                current_param_letter = token.value.upper()
                if idx + 1 < num_tokens and tokens[idx + 1].token_type == TokenType.PARAM_VALUE:
                    try:
                        parameters[current_param_letter] = float(tokens[idx + 1].value)
                    except ValueError:
                        pass
                    idx += 1

            elif token.token_type == TokenType.COMMENT_SYMBOL:
                comment_parts = [t.value for t in tokens[idx + 1:] if t.token_type == TokenType.COMMENT_TEXT]
                comment_text = "".join(comment_parts)
                break

            idx += 1

        return self._instantiate_command(
            line_number=line_number,
            raw_text=raw_text,
            code=command_code,
            parameters=parameters,
            comment=comment_text,
        )

    def _instantiate_command(
        self,
        line_number: int,
        raw_text: str,
        code: Optional[str],
        parameters: Dict[str, float],
        comment: Optional[str],
    ) -> Command:
        """Crea la instancia de Command o subclase apropiada según el código detectado."""

        if code is None:
            clean = comment if comment is not None else ""
            return CommentCommand(
                line_number=line_number,
                raw_text=raw_text,
                code=None,
                parameters=parameters,
                comment=comment,
                clean_text=clean,
            )

        if code in {"G0", "G1", "G2", "G3", "G5"}:
            return MoveCommand(
                line_number=line_number,
                raw_text=raw_text,
                code=code,
                parameters=parameters,
                comment=comment,
                x=parameters.get("X"),
                y=parameters.get("Y"),
                z=parameters.get("Z"),
                e=parameters.get("E"),
                f=parameters.get("F"),
            )

        if code in {"M104", "M109", "M140", "M190"}:
            is_bed = code in {"M140", "M190"}
            wait_for_heating = code in {"M109", "M190"}
            target_temp = parameters.get("S") if "S" in parameters else parameters.get("R")
            tool_idx = int(parameters.get("T", 0.0))

            return TemperatureCommand(
                line_number=line_number,
                raw_text=raw_text,
                code=code,
                parameters=parameters,
                comment=comment,
                target_temperature=target_temp,
                tool_index=tool_idx,
                is_bed=is_bed,
                wait_for_heating=wait_for_heating,
            )

        return Command(
            line_number=line_number,
            raw_text=raw_text,
            code=code,
            parameters=parameters,
            comment=comment,
        )

    def parse_stream(self, token_stream: Iterator[List[Token]]) -> Document:
        """Procesa el flujo de tokens completo y construye el objeto inmune Document."""
        commands: List[Command] = [
            self.parse_line_tokens(line_tokens)
            for line_tokens in token_stream
            if line_tokens
        ]
        return Document(commands=tuple(commands))