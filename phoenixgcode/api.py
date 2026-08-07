"""
API Pública de PhoenixGCode.

Fachada principal que expone los servicios de la biblioteca para consumo
de frontends, plugins (Cura, OctoPrint, Print2Go) y APIs externas.
"""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from dataclasses import asdict

from phoenixgcode.reader.reader import GCodeReader
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.analyzer.analyzer import GCodeAnalyzer, AnalysisResult
from phoenixgcode.transformer.recovery.planner import RecoveryPlanner
from phoenixgcode.transformer.recovery.builder import RecoveryBuilder
from phoenixgcode.writer.writer import GCodeWriter
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType
from phoenixgcode.model.recovery_plan import RecoveryPlan, RecoveryCandidate


class PhoenixGCodeAPI:
    """
    Punto de entrada único y oficial para clientes externos.
    
    Toda la lógica de análisis, interpretación y transformación reside aquí.
    Los plugins simplemente invocan estos métodos.
    """

    @staticmethod
    def analyze_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Lee y analiza un archivo G-code, devolviendo un resumen estructurado listo para JSON.

        Args:
            file_path: Ruta al archivo G-code.

        Returns:
            Diccionario con metadatos, capas, alturas y snapshots detectados.
        """
        reader = GCodeReader(file_path)
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()

        tokens = tokenizer.tokenize_stream(reader.read_lines())
        document = parser.parse_stream(tokens)
        timeline = interpreter.interpret(document)
        analysis = analyzer.analyze(document, timeline)

        return {
            "total_commands": len(document),
            "total_layers": analysis.layer_index.total_layers,
            "max_z_height": analysis.max_z_height,
            "first_extrusion_line": analysis.first_extrusion_command_index,
            "last_extrusion_line": analysis.last_extrusion_command_index,
            "available_z_heights": analysis.z_index.sorted_z_heights,
        }

    @staticmethod
    def plan_recovery(
        file_path: Union[str, Path],
        measured_z: float,
        strategy_name: str = "HOME_XY",
        override_hotend_temp: Optional[float] = None,
        override_bed_temp: Optional[float] = None,
        override_fan_speed: Optional[float] = None,
        z_hop_distance: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Crea una propuesta de RecoveryPlan inspeccionable para el cliente.

        Returns:
            Diccionario con la información del candidato sugerido y el estado a restaurar.
        """
        reader = GCodeReader(file_path)
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()
        planner = RecoveryPlanner()

        document = parser.parse_stream(tokenizer.tokenize_stream(reader.read_lines()))
        timeline = interpreter.interpret(document)
        analysis = analyzer.analyze(document, timeline)

        strategy = RecoveryStrategyType[strategy_name]
        settings = RecoverySettings(
            measured_z=measured_z,
            strategy=strategy,
            override_hotend_temp=override_hotend_temp,
            override_bed_temp=override_bed_temp,
            override_fan_speed=override_fan_speed,
            z_hop_distance=z_hop_distance,
        )

        candidates = planner.find_candidates(document, timeline, analysis, settings)
        if not candidates:
            raise ValueError(f"No se encontraron puntos de recuperación para Z={measured_z}mm")

        best_candidate = candidates[0]
        plan = planner.create_plan(best_candidate, settings)

        snap = plan.reconstructed_snapshot
        return {
            "candidate": {
                "line_number": best_candidate.line_number,
                "layer_index": best_candidate.layer_index,
                "target_z": best_candidate.target_z,
                "confidence_score": best_candidate.confidence_score,
            },
            "reconstructed_state": {
                "x": snap.position.x,
                "y": snap.position.y,
                "z": snap.position.z,
                "extruder_e": snap.extruder_position,
                "feedrate": snap.feedrate,
                "bed_temp": settings.override_bed_temp or snap.bed_temperature,
                "hotend_temp": settings.override_hotend_temp or snap.hotend_temperatures.get(snap.active_tool, 200.0),
                "fan_speed": settings.override_fan_speed or snap.fan_speed,
            },
            "preamble_preview": [cmd.raw_text for cmd in plan.preamble_commands if cmd.raw_text],
            "resume_preview": [cmd.raw_text for cmd in plan.resume_commands if cmd.raw_text],
        }

    @staticmethod
    def execute_recovery(
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        measured_z: float,
        strategy_name: str = "HOME_XY",
        override_hotend_temp: Optional[float] = None,
        override_bed_temp: Optional[float] = None,
        override_fan_speed: Optional[float] = None,
        z_hop_distance: float = 10.0,
    ) -> str:
        """
        Ejecuta el ciclo completo y escribe el archivo Recovery.gcode en la ruta especificada.

        Returns:
            Ruta absoluta del archivo generado.
        """
        reader = GCodeReader(input_path)
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()
        planner = RecoveryPlanner()
        builder = RecoveryBuilder()
        writer = GCodeWriter()

        document = parser.parse_stream(tokenizer.tokenize_stream(reader.read_lines()))
        timeline = interpreter.interpret(document)
        analysis = analyzer.analyze(document, timeline)

        strategy = RecoveryStrategyType[strategy_name]
        settings = RecoverySettings(
            measured_z=measured_z,
            strategy=strategy,
            override_hotend_temp=override_hotend_temp,
            override_bed_temp=override_bed_temp,
            override_fan_speed=override_fan_speed,
            z_hop_distance=z_hop_distance,
        )

        candidates = planner.find_candidates(document, timeline, analysis, settings)
        if not candidates:
            raise ValueError(f"No se encontraron puntos de recuperación para Z={measured_z}mm")

        plan = planner.create_plan(candidates[0], settings)
        recovery_doc = builder.build_document(document, plan, settings)
        result_path = writer.write_to_file(recovery_doc, output_path)

        return str(result_path.resolve())