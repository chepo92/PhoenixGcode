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

        settings = RecoverySettings(
            measured_z=0.4,
            z_tolerance=0.05,
            strategy=RecoveryStrategyType.HOME_XY,
            override_hotend_temp=210.0,
        )

        candidates = planner.find_candidates(doc, timeline, analysis, settings)

        assert len(candidates) > 0
        top_candidate = candidates[0]
        assert abs(top_candidate.target_z - 0.4) < 0.001
        assert top_candidate.confidence_score > 0.0  # Confianza positiva válida

        plan = planner.create_plan(top_candidate, settings)
        assert len(plan.preamble_commands) > 0

    def test_candidates_limit_and_confidence(self, pipeline):
        """
        Verifica que ante un G-code con cientos de movimientos en la misma capa,
        el Planner retorne una cantidad acotada (entre 1 y 10) de candidatos significativos
        y con confidence_score válido (> 0.0).
        """
        tokenizer, parser, interpreter, analyzer, planner = pipeline

        # Generar simulación con 100 movimientos dentro del mismo Z=0.4
        lines = [
            (1, "G21"),
            (2, "G90"),
            (3, "M82"),
            (4, "G1 Z0.4 F1200"),
        ]
        for i in range(1, 100):
            lines.append((4 + i, f"G1 X{i} Y{i} E{i*0.1}"))

        token_stream = (tokenizer.tokenize_line(num, txt) for num, txt in lines)
        doc = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(doc)
        analysis = analyzer.analyze(doc, timeline)

        settings = RecoverySettings(measured_z=0.5)  # Medido .5 para Z=0.4
        candidates = planner.find_candidates(doc, timeline, analysis, settings)

        # Regla: La lista de candidatos debe estar acotada entre 1 y 10 (no 240+ elementos)
        assert 1 <= len(candidates) <= 10
        # Regla: Ningún candidato debe tener 0.0% de confianza
        assert all(c.confidence_score > 0.0 for c in candidates)