"""
Módulo Recovery Planner de PhoenixGCode.
"""

from typing import List, Optional
from phoenixgcode.model.command import Command, MoveCommand, TemperatureCommand
from phoenixgcode.model.document import Document
from phoenixgcode.model.snapshot import ExecutionTimeline
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType
from phoenixgcode.model.recovery_plan import RecoveryCandidate, RecoveryPlan
from phoenixgcode.analyzer.analyzer import AnalysisResult


class RecoveryPlanner:
    """Planificador de recuperación de impresión para PhoenixGCode."""

    def find_candidates(
        self,
        document: Document,
        timeline: ExecutionTimeline,
        analysis: AnalysisResult,
        settings: RecoverySettings,
        max_candidates: int = 10,
    ) -> List[RecoveryCandidate]:
        """
        Encuentra candidatos de recuperación significativos (cambios de Z o inicios de sección)
        compatibles con la altura Z medida.
        """
        target_z = settings.measured_z
        sorted_zs = analysis.z_index.sorted_z_heights

        if not sorted_zs:
            return []

        # 1. Identificar las alturas Z más cercanas (por debajo y por encima)
        target_heights: List[float] = []
        
        # Encontrar el Z exacto o los dos Z circundantes
        lower_z = None
        upper_z = None
        for z in sorted_zs:
            if z <= target_z:
                lower_z = z
            if z >= target_z and upper_z is None:
                upper_z = z

        if lower_z is not None:
            target_heights.append(lower_z)
        if upper_z is not None and upper_z not in target_heights:
            target_heights.append(upper_z)

        # Si no encontró ninguno por la búsqueda anterior, usar el más cercano genérico
        if not target_heights:
            closest = analysis.z_index.find_closest_z(target_z)
            if closest is not None:
                target_heights.append(closest)

        raw_candidates: List[RecoveryCandidate] = []

        for h_z in target_heights:
            matching_cmd_indices = analysis.z_index.get_commands_at_z(h_z, tolerance=0.01)
            last_z_seen: Optional[float] = None

            for cmd_idx in matching_cmd_indices:
                cmd = document[cmd_idx]
                snap = timeline.snapshots[cmd_idx] if cmd_idx < len(timeline.snapshots) else None

                if snap is None:
                    continue

                is_z_change_move = isinstance(cmd, MoveCommand) and cmd.z is not None
                is_first_extruding_move = (
                    isinstance(cmd, MoveCommand)
                    and cmd.e is not None
                    and (last_z_seen is None or abs(snap.position.z - last_z_seen) > 0.001)
                )

                if not (is_z_change_move or is_first_extruding_move):
                    continue

                last_z_seen = snap.position.z

                # 1. Intentar obtener capa por el índice del snapshot si existe
                layer_idx = 0
                if snap.current_layer_index is not None and snap.current_layer_index > 0:
                    layer_info = analysis.layer_index.get_layer(snap.current_layer_index)
                    if layer_info:
                        layer_idx = getattr(layer_info, 'layer_index', snap.current_layer_index)
                    else:
                        layer_idx = snap.current_layer_index

                # 2. Fallback: Resolver el número de capa mediante la altura Z en el análisis
                if layer_idx == 0 and hasattr(analysis, "z_index") and hasattr(analysis.z_index, "sorted_z_heights"):
                    z_heights = analysis.z_index.sorted_z_heights
                    current_z = snap.position.z
                    for idx, z_val in enumerate(z_heights):
                        if abs(z_val - current_z) < 0.01:
                            layer_idx = idx + 1  # Capas numeradas desde 1 (Capa 1, Capa 2...)
                            break

                # Cálculo de confianza
                z_err = abs(snap.position.z - target_z)
                confidence = max(0.4, 1.0 - z_err)
                if isinstance(cmd, MoveCommand) and cmd.e is not None:
                    confidence = min(1.0, confidence + 0.1)

                candidate = RecoveryCandidate(
                    line_number=cmd.line_number,
                    layer_index=layer_idx,
                    target_z=snap.position.z,
                    snapshot=snap,
                    confidence_score=round(confidence, 3),
                )
                raw_candidates.append(candidate)

        # Si aún no hay candidatos en cambios de Z, agregar el primer comando del nivel
        if not raw_candidates:
            for h_z in target_heights:
                matching = analysis.z_index.get_commands_at_z(h_z)
                if matching:
                    idx = matching[0]
                    c_cmd = document[idx]
                    c_snap = timeline.snapshots[idx]
                    raw_candidates.append(
                        RecoveryCandidate(
                            line_number=c_cmd.line_number,
                            layer_index=c_snap.current_layer_index or 0,
                            target_z=c_snap.position.z,
                            snapshot=c_snap,
                            confidence_score=0.8,
                        )
                    )

        # Ordenar por cercanía a target_z y luego por confianza
        raw_candidates.sort(key=lambda c: (abs(c.target_z - target_z), -c.confidence_score))

        return raw_candidates[:max_candidates]

    def create_plan(
        self,
        candidate: RecoveryCandidate,
        settings: RecoverySettings,
    ) -> RecoveryPlan:
        """Construye un RecoveryPlan editable a partir del candidato seleccionado."""
        snap = candidate.snapshot

        bed_temp = settings.override_bed_temp if settings.override_bed_temp is not None else snap.bed_temperature
        active_hotend_temp = (
            settings.override_hotend_temp
            if settings.override_hotend_temp is not None
            else snap.hotend_temperatures.get(snap.active_tool, 200.0)
        )
        fan_speed = (
            settings.override_fan_speed
            if settings.override_fan_speed is not None
            else snap.fan_speed
        )

        preamble: List[Command] = []
        preamble.append(Command(line_number=0, raw_text="G21 ; Metric units", code="G21"))
        pos_mode_code = "G90" if snap.positioning_mode.name == "ABSOLUTE" else "G91"
        preamble.append(Command(line_number=0, raw_text=f"{pos_mode_code} ; Positioning mode", code=pos_mode_code))
        ext_mode_code = "M82" if snap.extrusion_mode.name == "ABSOLUTE" else "M83"
        preamble.append(Command(line_number=0, raw_text=f"{ext_mode_code} ; Extrusion mode", code=ext_mode_code))

        if bed_temp > 0:
            preamble.append(
                TemperatureCommand(
                    line_number=0,
                    raw_text=f"M190 S{bed_temp:.1f} ; Wait bed temp",
                    code="M190",
                    parameters={"S": bed_temp},
                    target_temperature=bed_temp,
                    is_bed=True,
                    wait_for_heating=True,
                )
            )

        preamble.append(
            TemperatureCommand(
                line_number=0,
                raw_text=f"M109 S{active_hotend_temp:.1f} T{snap.active_tool} ; Wait hotend temp",
                code="M109",
                parameters={"S": active_hotend_temp, "T": float(snap.active_tool)},
                target_temperature=active_hotend_temp,
                tool_index=snap.active_tool,
                is_bed=False,
                wait_for_heating=True,
            )
        )

        if settings.strategy == RecoveryStrategyType.HOME_XY:
            preamble.append(Command(line_number=0, raw_text="G28 X Y ; Home XY safely", code="G28", parameters={"X": 0.0, "Y": 0.0}))
        elif settings.strategy == RecoveryStrategyType.HOME_XYZ:
            preamble.append(Command(line_number=0, raw_text="G28 ; Home XYZ", code="G28"))

        if fan_speed > 0:
            preamble.append(Command(line_number=0, raw_text=f"M106 S{int(fan_speed)} ; Restore Fan", code="M106", parameters={"S": fan_speed}))

        for line in settings.custom_prime_script:
            preamble.append(Command(line_number=0, raw_text=line, code=line.split()[0] if line.strip() else None))

        preamble.append(
            Command(
                line_number=0,
                raw_text=f"G92 E{snap.extruder_position:.4f} ; Restore Extruder E",
                code="G92",
                parameters={"E": snap.extruder_position},
            )
        )

        resume: List[Command] = []
        safe_z = candidate.target_z + settings.z_hop_distance
        resume.append(
            MoveCommand(
                line_number=0,
                raw_text=f"G1 Z{safe_z:.3f} F3000 ; Z-hop clearance",
                code="G1",
                parameters={"Z": safe_z, "F": 3000.0},
                z=safe_z,
                f=3000.0,
            )
        )

        resume.append(
            MoveCommand(
                line_number=0,
                raw_text=f"G1 X{snap.position.x:.3f} Y{snap.position.y:.3f} F3000 ; Move to X/Y target",
                code="G1",
                parameters={"X": snap.position.x, "Y": snap.position.y, "F": 3000.0},
                x=snap.position.x,
                y=snap.position.y,
                f=3000.0,
            )
        )

        resume.append(
            MoveCommand(
                line_number=0,
                raw_text=f"G1 Z{candidate.target_z:.3f} F600 ; Lower to layer Z",
                code="G1",
                parameters={"Z": candidate.target_z, "F": 600.0},
                z=candidate.target_z,
                f=600.0,
            )
        )

        if snap.feedrate > 0:
            resume.append(
                MoveCommand(
                    line_number=0,
                    raw_text=f"G1 F{snap.feedrate:.1f} ; Restore original Feedrate",
                    code="G1",
                    parameters={"F": snap.feedrate},
                    f=snap.feedrate,
                )
            )

        return RecoveryPlan(
            selected_candidate=candidate,
            reconstructed_snapshot=snap,
            preamble_commands=preamble,
            resume_commands=resume,
            settings_used=settings,
        )