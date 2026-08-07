"""
Pruebas unitarias para el módulo RecoveryBuilder de PhoenixGCode.
"""

import pytest
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.analyzer.analyzer import GCodeAnalyzer
from phoenixgcode.transformer.recovery.planner import RecoveryPlanner
from phoenixgcode.transformer.recovery.builder import RecoveryBuilder
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType
from phoenixgcode.model.document import Document


class TestRecoveryBuilder:

    @pytest.fixture
    def setup_pipeline(self):
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()
        planner = RecoveryPlanner()
        builder = RecoveryBuilder()
        return tokenizer, parser, interpreter, analyzer, planner, builder

    def _create_document(self, tokenizer, parser, lines):
        token_stream = (tokenizer.tokenize_line(num, txt) for num, txt in lines)
        return parser.parse_stream(token_stream)

    @pytest.mark.parametrize(
        "strategy, expected_text_flag",
        [
            (RecoveryStrategyType.MANUAL_POSITION, "MANUAL_POSITION"),
            (RecoveryStrategyType.HOME_XY, "HOME_XY"),
            (RecoveryStrategyType.HOME_XYZ, "HOME_XYZ"),
            (RecoveryStrategyType.CUSTOM_SCRIPT, "CUSTOM_SCRIPT"),
        ],
    )
    def test_recovery_strategies_assembly(self, setup_pipeline, strategy, expected_text_flag):
        """Verifica que el Builder arme correctamente el nuevo Document para cada RecoveryStrategy."""
        tokenizer, parser, interpreter, analyzer, planner, builder = setup_pipeline

        lines = [
            (1, "G21"),
            (2, "G90"),
            (3, "M82"),
            (4, "G1 Z0.2 F1200"),
            (5, "G1 X10 Y10 E0.5"),
            (6, "G1 Z0.4"),
            (7, "G1 X20 Y20 E1.0"),
            (8, "G1 X30 Y30 E1.5"),
        ]

        doc = self._create_document(tokenizer, parser, lines)
        timeline = interpreter.interpret(doc)
        analysis = analyzer.analyze(doc, timeline)

        custom_script = ["M117 Custom Purge", "G1 E5 F300"] if strategy == RecoveryStrategyType.CUSTOM_SCRIPT else []

        settings = RecoverySettings(
            measured_z=0.4,
            strategy=strategy,
            custom_prime_script=custom_script,
        )

        candidates = planner.find_candidates(doc, timeline, analysis, settings)
        plan = planner.create_plan(candidates[0], settings)

        new_doc = builder.build_document(doc, plan, settings)

        # 1. Debe devolver un objeto Document de Python
        assert isinstance(new_doc, Document)
        assert len(new_doc) > len(doc)  # Incluye preámbulos y encabezados

        # 2. Verificar que se inyectó la estrategia correcta
        full_text = "\n".join(cmd.raw_text for cmd in new_doc)
        assert expected_text_flag in full_text

        # 3. Verificar la presencia del corte original de la reanudación (G1 X20 Y20 E1.0)
        assert "G1 X20 Y20 E1.0" in full_text

    def test_builder_does_not_write_files(self, setup_pipeline):
        """
        Regla de Oro: RecoveryBuilder NUNCA realiza I/O ni escribe archivos a disco.
        """
        tokenizer, parser, interpreter, analyzer, planner, builder = setup_pipeline

        lines = [(1, "G1 Z0.2 E0.1")]
        doc = self._create_document(tokenizer, parser, lines)
        timeline = interpreter.interpret(doc)
        analysis = analyzer.analyze(doc, timeline)

        settings = RecoverySettings(measured_z=0.2)
        candidates = planner.find_candidates(doc, timeline, analysis, settings)
        plan = planner.create_plan(candidates[0], settings)

        result_doc = builder.build_document(doc, plan, settings)

        # No existen métodos de I/O
        assert not hasattr(builder, "write")
        assert not hasattr(builder, "save")
        assert isinstance(result_doc, Document)