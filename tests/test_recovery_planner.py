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
        """Verifica la búsqueda de candidatos, la asignación de capa y la generación de un plan editable."""
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
        
        # Validar que el número de capa NO sea 0
        assert top_candidate.layer_index > 0, f"Se esperaba layer_index > 0, pero se obtuvo {top_candidate.layer_index}"

        plan = planner.create_plan(top_candidate, settings)
        assert len(plan.preamble_commands) > 0

    def test_candidates_limit_and_confidence(self, pipeline):
        """
        Verifica que ante un G-code con cientos de movimientos en la misma capa,
        el Planner retorne una cantidad acotada (entre 1 y 10) de candidatos significativos,
        con confidence_score válido (> 0.0) y números de capa mayores a cero.
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

        # Regla: La lista de candidatos debe estar acotada entre 1 y 10
        assert 1 <= len(candidates) <= 10
        # Regla: Ningún candidato debe tener 0.0% de confianza
        assert all(c.confidence_score > 0.0 for c in candidates)
        # Regla: Todos los candidatos deben tener layer_index > 0
        assert all(c.layer_index > 0 for c in candidates), "Se encontraron candidatos con layer_index == 0"

    def test_recovery_planner_real_cura_gcode(self, pipeline):
        """
        Verifica el cálculo de candidatos y el layer_index utilizando
        un extracto real generado por Cura 5.x para Ender 3.
        """
        tokenizer, parser, interpreter, analyzer, planner = pipeline

        cura_gcode_sample = """
;FLAVOR:Marlin
;TIME:2528
;Filament used: 1.48216m
;Layer height: 0.2
;MINX:104.5
;MINY:104.5
;MINZ:0.2
;MAXX:130.5
;MAXY:130.5
;MAXZ:20
;TARGET_MACHINE.NAME:Creality Ender-3
;Generated with Cura_SteamEngine 5.10.2
M140 S50
M105
M104 S210
M105
M109 S210
; Ender 3 Custom Start G-code
G92 E0
G28 ; Home all axes
G1 Z2.0 F3000
G1 X0.1 Y20 Z0.3 F5000.0
G1 X0.1 Y200.0 Z0.3 F1500.0 E15 ; Draw line 1
G1 X0.4 Y200.0 Z0.3 F5000.0
G1 X0.4 Y20 Z0.3 F1500.0 E30 ; Draw line 2
G92 E0
G1 Z2.0 F3000
G1 X5 Y20 Z0.3 F5000.0
M82 ; absolute extrusion mode
G92 E0
G1 F2700 E-5
;LAYER_COUNT:100
;LAYER:0
M107
G0 F6000 X105.091 Y105.671 Z0.2
;TYPE:SKIRT
G1 F2700 E0
G1 F1200 X105.678 Y105.126 E0.02664
G1 X106.471 Y104.653 E0.05735
;MESH:NONMESH
G0 F300 X108.804 Y126.34 Z0.4
;TIME_ELAPSED:98.742767
;LAYER:1
M106 S85
;TYPE:WALL-INNER
;MESH:Test_Cube.stl
G1 F1500 X126.9 Y108.1 E58.08876
G1 X108.1 Y108.1 E58.71406
G1 X108.1 Y126.9 E59.33935
G1 X126.9 Y126.9 E59.96464
"""

        lines = [(idx + 1, line) for idx, line in enumerate(cura_gcode_sample.strip().split('\n'))]
        token_stream = (tokenizer.tokenize_line(num, txt) for num, txt in lines)
        doc = parser.parse_stream(token_stream)
        timeline = interpreter.interpret(doc)
        analysis = analyzer.analyze(doc, timeline)

        # Consultar la recuperación para Z = 0.4mm (Capa 1 de Cura)
        settings = RecoverySettings(
            measured_z=0.4,
            z_tolerance=0.05,
            strategy=RecoveryStrategyType.HOME_XY
        )

        candidates = planner.find_candidates(doc, timeline, analysis, settings)

        assert len(candidates) > 0, "Debe detectar candidatos en Z=0.4mm"
        
        candidato = candidates[0]
        
        # Validaciones estrictas:
        assert abs(candidato.target_z - 0.4) < 0.001, f"Altura incorrecta: {candidato.target_z}"
        assert candidato.layer_index >= 1, f"El layer_index no debe ser 0. Se obtuvo: {candidato.layer_index}"
        assert candidato.confidence_score > 0.0, "La confianza debe ser mayor a cero"

        # Crear el plan y verificar que reconstruya la extrusión requerida
        plan = planner.create_plan(candidato, settings)
        assert plan.reconstructed_snapshot.position.z == 0.4