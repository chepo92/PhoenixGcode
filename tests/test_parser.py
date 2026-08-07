"""
Pruebas unitarias para el módulo Parser de PhoenixGCode.
"""

import pytest
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.model.command import (
    Command,
    MoveCommand,
    TemperatureCommand,
    CommentCommand,
)
from phoenixgcode.model.document import Document


class TestGCodeParser:

    @pytest.fixture
    def tokenizer(self):
        return GCodeTokenizer()

    @pytest.fixture
    def parser(self):
        return GCodeParser()

    def test_parse_move_command(self, tokenizer, parser):
        """Verifica el parsing de comandos de movimiento a objetos MoveCommand."""
        line = "G1 X10.5 Y20.0 Z0.2 E0.12 F1200 ; Extruyendo"
        tokens = tokenizer.tokenize_line(1, line)
        cmd = parser.parse_line_tokens(tokens)

        assert isinstance(cmd, MoveCommand)
        assert cmd.code == "G1"
        assert cmd.x == 10.5
        assert cmd.y == 20.0
        assert cmd.z == 0.2
        assert cmd.e == 0.12
        assert cmd.f == 1200.0
        assert cmd.comment == " Extruyendo"
        assert cmd.raw_text == line

    def test_parse_unordered_parameters(self, tokenizer, parser):
        """Verifica que el Parser sea agnóstico al orden de los parámetros."""
        line = "G1 E0.5 F300 Z0.4 Y10.0 X5.0"
        tokens = tokenizer.tokenize_line(2, line)
        cmd = parser.parse_line_tokens(tokens)

        assert isinstance(cmd, MoveCommand)
        assert cmd.x == 5.0
        assert cmd.y == 10.0
        assert cmd.z == 0.4
        assert cmd.e == 0.5
        assert cmd.f == 300.0

    def test_parse_temperature_command(self, tokenizer, parser):
        """Verifica el parsing de comandos de temperatura para Hotend y Bed."""
        # M109 - Esperar temperatura de Hotend
        line1 = "M109 S215 T0"
        tokens1 = tokenizer.tokenize_line(3, line1)
        cmd1 = parser.parse_line_tokens(tokens1)

        assert isinstance(cmd1, TemperatureCommand)
        assert cmd1.code == "M109"
        assert cmd1.target_temperature == 215.0
        assert cmd1.tool_index == 0
        assert cmd1.is_bed is False
        assert cmd1.wait_for_heating is True

        # M140 - Ajustar temperatura de cama sin esperar
        line2 = "M140 S60"
        tokens2 = tokenizer.tokenize_line(4, line2)
        cmd2 = parser.parse_line_tokens(tokens2)

        assert isinstance(cmd2, TemperatureCommand)
        assert cmd2.code == "M140"
        assert cmd2.target_temperature == 60.0
        assert cmd2.is_bed is True
        assert cmd2.wait_for_heating is False

    def test_parse_comment_command(self, tokenizer, parser):
        """Verifica el parsing de líneas de comentario o vacías."""
        line = "; LAYER: 5 - Impresion activa"
        tokens = tokenizer.tokenize_line(5, line)
        cmd = parser.parse_line_tokens(tokens)

        assert isinstance(cmd, CommentCommand)
        assert cmd.code is None
        assert cmd.clean_text == " LAYER: 5 - Impresion activa"
        assert cmd.line_number == 5

    def test_parse_generic_command(self, tokenizer, parser):
        """Verifica comandos no especializados como G28 u M106."""
        line = "G28 X0 Y0 ; Home XY"
        tokens = tokenizer.tokenize_line(6, line)
        cmd = parser.parse_line_tokens(tokens)

        assert type(cmd) is Command
        assert cmd.code == "G28"
        assert cmd.parameters == {"X": 0.0, "Y": 0.0}
        assert cmd.comment == " Home XY"

    def test_parse_stream_to_document(self, tokenizer, parser):
        """Verifica la construcción de un Document inmutable a partir de un flujo de tokens."""
        lines = [
            (1, "; Inicio"),
            (2, "G21"),
            (3, "G90"),
            (4, "G1 X10 Y10 E1.0 F1500")
        ]
        token_stream = (tokenizer.tokenize_line(line_num, line_txt) for line_num, line_txt in lines)
        document = parser.parse_stream(token_stream)

        assert isinstance(document, Document)
        assert len(document) == 4
        assert isinstance(document[0], CommentCommand)
        assert document[3].code == "G1"
        assert isinstance(document[3], MoveCommand)

    def test_parser_does_not_interpret_meaning(self, tokenizer, parser):
        """
        Regla de Oro: El Parser solo convierte sintaxis, nunca valida la semántica.
        Un comando con valores físicamente absurdos debe ser creado tal cual.
        """
        line = "G1 X-999999 Y999999 E-50.0 F0.0"
        tokens = tokenizer.tokenize_line(10, line)
        cmd = parser.parse_line_tokens(tokens)

        assert isinstance(cmd, MoveCommand)
        assert cmd.x == -999999.0
        assert cmd.y == 999999.0
        assert cmd.e == -50.0
        assert cmd.f == 0.0