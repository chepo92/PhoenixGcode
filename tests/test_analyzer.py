"""
Pruebas unitarias para el módulo Analyzer de PhoenixGCode.
"""

import pytest
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.analyzer.analyzer import GCodeAnalyzer
from phoenixgcode.model.command import CommandType


class TestGCodeAnalyzer:

    @pytest.fixture
    def pipeline(self):
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()
        return tokenizer, parser, interpreter, analyzer

    def test_analysis_indices_and_extrusion_detection(self, pipeline):
        """Verifica la construcción de índices y la detección del primer y último movimiento con extrusión."""
        tokenizer, parser, interpreter, analyzer = pipeline

        lines = [
            (1, "; Header comment"),
            (2, "G21"),
            (3, "G90"),
            (4, "M82"),
            (5, "M104 S200"),
            (6, "; LAYER:0"),
            (7, "G1 Z0.2 F1200"),
            (8, "G1 X10 Y10 E0.5 F1500 ; First Extrusion"),
            (9, "G1 X20 Y10 E1.0"),
            (10, "; LAYER:1"),
            (11, "G1 Z0.4"),
            (12, "G1 X20 Y20 E1.5 ; Last Extrusion"),
            (13, "M104 S0")
        ]

        token_stream = (tokenizer.tokenize_line(line_num, txt) for line_num, txt in lines)
        doc = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(doc)
        result = analyzer.analyze(doc, timeline)

        # 1. Verificar índices de extrusión
        assert result.first_extrusion_command_index == 7   # Línea 8 (G1 X10 Y10 E0.5)
        assert result.last_extrusion_command_index == 11   # Línea 12 (G1 X20 Y20 E1.5)

        # 2. Verificar SnapshotIndex O(1)
        snap_line_8 = result.snapshot_index.get_by_line(8)
        assert snap_line_8 is not None
        assert snap_line_8.position.x == 10.0
        assert snap_line_8.extruder_position == 0.5

        # 3. Verificar ZIndex
        cmds_at_z02 = result.z_index.get_commands_at_z(0.2)
        assert len(cmds_at_z02) > 0
        assert result.max_z_height == 0.4

        # 4. Verificar LayerIndex
        assert result.layer_index.total_layers >= 2
        layer0 = result.layer_index.get_layer(0)
        assert layer0 is not None
        assert layer0.start_line == 6  # Inicia exactamente en la etiqueta '; LAYER:0' de la línea 6

        # 5. Verificar CommandIndex
        temp_cmds = result.command_index.get_indices_by_type(CommandType.TEMPERATURE)
        assert len(temp_cmds) == 2  # M104 S200 y M104 S0
        assert len(result.command_index.comment_lines) > 0

    def test_analyzer_does_not_modify_document(self, pipeline):
        """Regla de Oro: El Analyzer NO modifica el Document."""
        tokenizer, parser, interpreter, analyzer = pipeline

        lines = [(1, "G1 X5 Y5 E0.1")]
        token_stream = (tokenizer.tokenize_line(line_num, txt) for line_num, txt in lines)
        doc = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(doc)

        original_len = len(doc)
        _ = analyzer.analyze(doc, timeline)

        assert len(doc) == original_len