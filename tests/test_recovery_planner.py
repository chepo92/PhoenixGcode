"""
Pruebas unitarias para el módulo RecoveryPlanner de PhoenixGCode.
"""

import pytest
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.analyzer.analyzer import GCodeAnalyzer
from phoenixgcode.transformer.recovery.planner import RecoveryPlanner
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType


class TestRecoveryPlanner:

    @pytest.fixture
    def pipeline(self):
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()
        planner = RecoveryPlanner()
        return tokenizer, parser, interpreter, analyzer, planner

    def test_find_candidates_and_build_editable_plan(self, pipeline):
        """Verifica la búsqueda de candidatos y la generación de un plan editable."""
        tokenizer, parser, interpreter, analyzer, planner = pipeline

        lines = [
            (1, "G21"),
            (2, "G90"),
            (3, "M82"),
            (4, "M104 S200"),
            (5, "M140 S60"),
            (6, "G1 Z0.2 F1200"),
            (7, "G1 X10 Y10 E0.5 F1500"),
            (8, "G1 Z0.4"),
            (9, "G1 X15 Y15 E1.0"),
            (10, "G1 X20 Y20 E1.5")
        ]

        token_stream = (tokenizer.tokenize_line(num, txt) for num, txt in lines)
        doc = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(doc)
        analysis = analyzer.analyze(doc, timeline)

        # Configuración buscando recuperarse a Z = 0.4 mm
        settings = RecoverySettings(
            measured_z=0.4,
            z_tolerance=0.05,
            strategy=RecoveryStrategyType.HOME_XY,
            override_hotend_temp=210.0,  # Cambio de temperatura personalizado
        )

        candidates = planner.find_candidates(doc, timeline, analysis, settings)

        assert len(candidates) > 0
        top_candidate = candidates[0]
        assert abs(top_candidate.target_z - 0.4) < 0.001

        plan = planner.create_plan(top_candidate, settings)

        # 1. Verificar preámbulo generado
        assert len(plan.preamble_commands) > 0
        # Debe incluir la temperatura override (210ºC)
        m109_cmd = [c for c in plan.preamble_commands if c.code == "M109"][0]
        assert m109_cmd.parameters["S"] == 210.0

        # 2. Verificar que el RecoveryPlan es 100% editable
        original_preamble_count = len(plan.preamble_commands)
        plan.preamble_commands.append(
            parser.parse_line_tokens(tokenizer.tokenize_line(0, "M117 Reanudando Impresion..."))
        )
        assert len(plan.preamble_commands) == original_preamble_count + 1

    def test_planner_does_not_generate_gcode_file(self, pipeline):
        """
        Regla de Oro: Planner solo devuelve estructuras de objetos (RecoveryPlan y Candidates),
        NUNCA escribe archivos ni emite texto crudo de G-code directo.
        """
        tokenizer, parser, interpreter, analyzer, planner = pipeline

        lines = [(1, "G1 Z0.2 E0.1")]
        doc = parser.parse_stream(tokenizer.tokenize_line(num, txt) for num, txt in lines)
        timeline = interpreter.interpret(doc)
        analysis = analyzer.analyze(doc, timeline)

        settings = RecoverySettings(measured_z=0.2)
        candidates = planner.find_candidates(doc, timeline, analysis, settings)
        plan = planner.create_plan(candidates[0], settings)

        assert hasattr(plan, "preamble_commands")
        assert hasattr(plan, "resume_commands")
        assert not hasattr(plan, "write_to_file")