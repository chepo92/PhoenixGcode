"""
API Pública de PhoenixGCode.

Fachada principal que expone los servicios de la biblioteca para consumo
de frontends (CLI, Cura, OctoPrint, Print2Go) y APIs externas.
"""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional

from phoenixgcode.reader.reader import GCodeReader
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer
from phoenixgcode.parser.parser import GCodeParser
from phoenixgcode.interpreter.interpreter import GCodeInterpreter
from phoenixgcode.analyzer.analyzer import GCodeAnalyzer
from phoenixgcode.transformer.recovery.planner import RecoveryPlanner
from phoenixgcode.transformer.recovery.builder import RecoveryBuilder
from phoenixgcode.writer.writer import GCodeWriter
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType


class PhoenixGCodeAPI:
    """Punto de entrada único y oficial para la interacción de todos los frontends con el core."""

    @staticmethod
    def analyze_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Devuelve un resumen completo del análisis de un archivo G-code."""
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
            "source_file": str(file_path),
            "total_lines": len(document),
            "total_layers": analysis.layer_index.total_layers,
            "max_z_height": analysis.max_z_height,
            "first_extrusion_line": analysis.first_extrusion_command_index,
            "last_extrusion_line": analysis.last_extrusion_command_index,
            "comment_count": len(analysis.command_index.comment_lines),
            "available_z_heights": analysis.z_index.sorted_z_heights,
        }

    @staticmethod
    def validate_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Valida que un archivo G-code pueda ser leído, tokenizado y parseado correctamente."""
        try:
            reader = GCodeReader(file_path)
            encoding = reader.detect_encoding()
            tokenizer = GCodeTokenizer()
            parser = GCodeParser()

            tokens = tokenizer.tokenize_stream(reader.read_lines(encoding=encoding))
            document = parser.parse_stream(tokens)

            return {
                "valid": True,
                "encoding": encoding,
                "total_commands": len(document),
                "error": None,
            }
        except Exception as e:
            return {
                "valid": False,
                "encoding": None,
                "total_commands": 0,
                "error": str(e),
            }

    @staticmethod
    def plan_recovery(
        file_path: Union[str, Path],
        measured_z: float,
        candidate_index: int = 0,
        strategy_name: str = "HOME_XY",
        override_hotend_temp: Optional[float] = None,
        override_bed_temp: Optional[float] = None,
        override_fan_speed: Optional[float] = None,
        z_hop_distance: float = 10.0,
    ) -> Dict[str, Any]:
        """Calcula los candidatos y construye la vista previa del Recovery Plan."""
        reader = GCodeReader(file_path)
        tokenizer = GCodeTokenizer()
        parser = GCodeParser()
        interpreter = GCodeInterpreter()
        analyzer = GCodeAnalyzer()
        planner = RecoveryPlanner()

        document = parser.parse_stream(tokenizer.tokenize_stream(reader.read_lines()))
        timeline = interpreter.interpret(document)
        analysis = analyzer.analyze(document, timeline)

        strategy = RecoveryStrategyType[strategy_name.upper()]
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

        if candidate_index < 0 or candidate_index >= len(candidates):
            raise IndexError(f"Índice de candidato {candidate_index} fuera de rango. Candidatos disponibles: {len(candidates)}")

        selected_candidate = candidates[candidate_index]
        plan = planner.create_plan(selected_candidate, settings)
        snap = plan.reconstructed_snapshot

        return {
            "source_file": str(file_path),
            "candidates": [
                {
                    "index": i,
                    "line_number": c.line_number,
                    "layer_index": c.layer_index,
                    "target_z": c.target_z,
                    "confidence_score": c.confidence_score,
                }
                for i, c in enumerate(candidates)
            ],
            "selected_candidate_index": candidate_index,
            "candidate": {
                "line_number": selected_candidate.line_number,
                "layer_index": selected_candidate.layer_index,
                "target_z": selected_candidate.target_z,
                "confidence_score": selected_candidate.confidence_score,
            },
            "reconstructed_state": {
                "x": snap.position.x,
                "y": snap.position.y,
                "z": snap.position.z,
                "extruder_e": snap.extruder_position,
                "feedrate": snap.feedrate,
                "bed_temp": settings.override_bed_temp if settings.override_bed_temp is not None else snap.bed_temperature,
                "hotend_temp": settings.override_hotend_temp if settings.override_hotend_temp is not None else snap.hotend_temperatures.get(snap.active_tool, 200.0),
                "fan_speed": settings.override_fan_speed if settings.override_fan_speed is not None else snap.fan_speed,
                "extrusion_mode": snap.extrusion_mode.name,
                "positioning_mode": snap.positioning_mode.name,
            },
            "strategy": strategy.name,
        }

    @staticmethod
    def execute_recovery(
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        measured_z: float,
        candidate_index: int = 0,
        strategy_name: str = "HOME_XY",
        override_hotend_temp: Optional[float] = None,
        override_bed_temp: Optional[float] = None,
        override_fan_speed: Optional[float] = None,
        z_hop_distance: float = 10.0,
    ) -> str:
        """Ejecuta el ciclo de transformación completo y compila el archivo Recovery.gcode."""
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

        strategy = RecoveryStrategyType[strategy_name.upper()]
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

        selected_candidate = candidates[candidate_index]
        plan = planner.create_plan(selected_candidate, settings)
        recovery_doc = builder.build_document(document, plan, settings)
        result_path = writer.write_to_file(recovery_doc, output_path)

        return str(result_path.resolve())