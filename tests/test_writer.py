"""
Pruebas unitarias para el módulo Writer de PhoenixGCode.
"""

from pathlib import Path
import pytest
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.writer.writer import GCodeWriter
from phoenixgcode.model.command import Command, MoveCommand, CommentCommand
from phoenixgcode.model.document import Document


class TestGCodeWriter:

    @pytest.fixture
    def setup_pipeline(self):
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        writer = GCodeWriter()
        return tokenizer, parser, writer

    def test_write_to_string_preserves_original_formatting_and_comments(self, setup_pipeline):
        """Verifica que el Writer mantenga exactamente los mismos espacios, comentarios y formato."""
        tokenizer, parser, writer = setup_pipeline

        original_lines = [
            "; Header comment",
            "G21 ; Metric values",
            "G90",
            "  G1   X10.50   Y-20.00   E0.1200  ; Preserving spaces",
            "M104 S200 T0",
            "; --- END HEADER ---"
        ]

        token_stream = (tokenizer.tokenize_line(idx + 1, txt) for idx, txt in enumerate(original_lines))
        doc = parser.parse_stream(token_stream)

        output_text = writer.write_to_string(doc)
        output_lines = output_text.split("\n")

        assert len(output_lines) == len(original_lines)
        for orig, out in zip(original_lines, output_lines):
            assert orig == out

    def test_format_dynamically_created_command(self, setup_pipeline):
        """Verifica que los comandos creados sin raw_text se formateen sintácticamente de forma limpia."""
        _, _, writer = setup_pipeline

        # Comando sintético creado sin raw_text
        cmd = MoveCommand(
            line_number=0,
            raw_text="",
            code="G1",
            parameters={"X": 10.5, "Y": 20.0, "E": 0.5},
            comment="Custom Move",
            x=10.5,
            y=20.0,
            e=0.5,
        )

        formatted = writer.format_command(cmd)

        assert "G1" in formatted
        assert "X10.5" in formatted
        assert "Y20" in formatted
        assert "E0.5" in formatted
        assert "; Custom Move" in formatted

    def test_write_to_file(self, setup_pipeline, tmp_path: Path):
        """Verifica que el Writer escriba físicamente el archivo .gcode a disco correctamente."""
        tokenizer, parser, writer = setup_pipeline

        lines = [
            "; PhoenixGCode Test File",
            "G21",
            "G1 X5 Y5 E0.1"
        ]

        token_stream = (tokenizer.tokenize_line(idx + 1, txt) for idx, txt in enumerate(lines))
        doc = parser.parse_stream(token_stream)

        output_file = tmp_path / "output_test.gcode"
        result_path = writer.write_to_file(doc, output_file)

        assert result_path.exists()
        file_content = result_path.read_text(encoding="utf-8")
        assert file_content == "\n".join(lines) + "\n"