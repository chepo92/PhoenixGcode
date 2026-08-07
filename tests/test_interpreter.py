"""
Pruebas unitarias para el módulo Interpreter de PhoenixGCode.
"""

import pytest
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.model.snapshot import PositioningMode, ExtrusionMode


class TestGCodeInterpreter:

    @pytest.fixture
    def pipeline(self):
        """Fixture que provee la cadena Reader/Tokenizer/Parser/Interpreter."""
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        return tokenizer, parser, interpreter

    def test_interpretation_motion_and_modes(self, pipeline):
        """Verifica la simulación de movimiento en modo absoluto y relativo."""
        tokenizer, parser, interpreter = pipeline

        lines = [
            (1, "G21 ; Millimeters"),
            (2, "G90 ; Absolute positioning"),
            (3, "M82 ; Absolute extrusion"),
            (4, "G1 F1500"),
            (5, "G1 X10 Y20 Z0.2 E1.0"),
            (6, "G91 ; Relative positioning"),
            (7, "M83 ; Relative extrusion"),
            (8, "G1 X5 Y-5 E0.5")
        ]

        token_stream = (tokenizer.tokenize_line(line_num, txt) for line_num, txt in lines)
        document = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(document)

        assert len(timeline.snapshots) == 8

        # Verificar snapshot tras línea 5 (Absoluto)
        snap5 = timeline.snapshots[4]
        assert snap5.position.x == 10.0
        assert snap5.position.y == 20.0
        assert snap5.position.z == 0.2
        assert snap5.extruder_position == 1.0
        assert snap5.feedrate == 1500.0
        assert snap5.positioning_mode == PositioningMode.ABSOLUTE
        assert snap5.extrusion_mode == ExtrusionMode.ABSOLUTE

        # Verificar snapshot tras línea 8 (Relativo)
        snap8 = timeline.snapshots[7]
        assert snap8.position.x == 15.0  # 10 + 5
        assert snap8.position.y == 15.0  # 20 - 5
        assert snap8.position.z == 0.2   # Sin cambio
        assert snap8.extruder_position == 1.5  # 1.0 + 0.5 (Extrusión relativa)
        assert snap8.positioning_mode == PositioningMode.RELATIVE
        assert snap8.extrusion_mode == ExtrusionMode.RELATIVE

    def test_temperature_and_fan_tracking(self, pipeline):
        """Verifica el rastreo de temperaturas de Hotend, Cama y Fan speed."""
        tokenizer, parser, interpreter = pipeline

        lines = [
            (1, "M140 S60 ; Bed temp"),
            (2, "M104 S210 T0 ; Hotend 0 temp"),
            (3, "M106 S128 ; Fan 50%"),
            (4, "M107 ; Fan off")
        ]

        token_stream = (tokenizer.tokenize_line(line_num, txt) for line_num, txt in lines)
        document = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(document)

        assert timeline.snapshots[0].bed_temperature == 60.0
        assert timeline.snapshots[1].hotend_temperatures[0] == 210.0
        assert timeline.snapshots[2].fan_speed == 128.0
        assert timeline.snapshots[3].fan_speed == 0.0

    def test_g92_position_reset(self, pipeline):
        """Verifica que G92 reinicie los contadores de posición especificados."""
        tokenizer, parser, interpreter = pipeline

        lines = [
            (1, "G1 E100.0 F1200"),
            (2, "G92 E0.0")
        ]

        token_stream = (tokenizer.tokenize_line(line_num, txt) for line_num, txt in lines)
        document = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(document)

        assert timeline.snapshots[0].extruder_position == 100.0
        assert timeline.snapshots[1].extruder_position == 0.0

    def test_document_is_not_modified(self, pipeline):
        """
        Regla de Oro: El Interpreter NUNCA modifica el Document original.
        """
        tokenizer, parser, interpreter = pipeline

        lines = [(1, "G1 X10 Y10 E1.0")]
        token_stream = (tokenizer.tokenize_line(line_num, txt) for line_num, txt in lines)
        document = parser.parse_stream(token_stream)

        # Capturar copia de datos originales
        original_len = len(document)
        original_raw = document[0].raw_text

        _ = interpreter.interpret(document)

        assert len(document) == original_len
        assert document[0].raw_text == original_raw