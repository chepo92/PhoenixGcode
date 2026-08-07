"""
Módulo Recovery Planner de PhoenixGCode.

Responsable de inspeccionar el Document, el ExecutionTimeline y los AnalysisResult 
para proponer candidatos de recuperación (RecoveryCandidate) a una altura Z medida
y construir un RecoveryPlan borrador 100% editable por el usuario.
"""

from typing import List, Optional
from phoenixgcode.model.command import Command, MoveCommand, TemperatureCommand
from phoenixgcode.model.document import Document
from phoenixgcode.model.snapshot import ExecutionTimeline, ExecutionSnapshot, Vector3D
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType
from phoenixgcode.model.recovery_plan import RecoveryCandidate, RecoveryPlan
from phoenixgcode.analyzer.analyzer import AnalysisResult


class RecoveryPlanner:
    """
    Planificador de recuperación de impresión para PhoenixGCode.

    Detecta la línea exacta de corte basándose en la altura Z física medida
    y construye un plan estructurado no destructivo.
    """

    def find_candidates(
        self,
        document: Document,
        timeline: ExecutionTimeline,
        analysis: AnalysisResult,
        settings: RecoverySettings,
    ) -> List[RecoveryCandidate]:
        """
        Encuentra todos los candidatos de recuperación compatibles con la altura Z medida.

        Args:
            document: Documento G-code parseado.
            timeline: Historia de ejecución simulada.
            analysis: Índices y metadatos calculados por Analyzer.
            settings: Configuración y tolerancia proporcionadas por el usuario.

        Returns:
            Lista de RecoveryCandidate ordenados por puntaje de confianza.
        """
        candidates: List[RecoveryCandidate] = []
        target_z = settings.measured_z
        tolerance = settings.z_tolerance

        # Búsqueda de índices de comandos ejecutados en el rango Z especificado
        matching_cmd_indices = analysis.z_index.get_commands_at_z(target_z, tolerance=tolerance)

        if not matching_cmd_indices:
            # Fallback: buscar la altura Z registrada más cercana si no hay coincidencia exacta
            closest_z = analysis.z_index.find_closest_z(target_z)
            if closest_z is not None:
                matching_cmd_indices = analysis.z_index.get_commands_at_z(closest_z, tolerance=tolerance)

        for cmd_idx in matching_cmd_indices:
            cmd = document[cmd_idx]
            snap = timeline.snapshots[cmd_idx] if cmd_idx < len(timeline.snapshots) else None

            if snap is None:
                continue

            # Dar mayor confianza a comandos de movimiento con extrusión
            is_move_with_extrusion = isinstance(cmd, MoveCommand) and cmd.e is not None
            layer_info = analysis.layer_index.get_layer(snap.current_layer_index or 0)
            layer_idx = layer_info.layer_index if layer_info else 0

            # Cálculo de score
            z_diff = abs(snap.position.z - target_z)
            confidence = max(0.0, 1.0 - (z_diff / (tolerance if tolerance > 0 else 0.1)))
            if is_move_with_extrusion:
                confidence = min(1.0, confidence * 1.2)

            candidate = RecoveryCandidate(
                line_number=cmd.line_number,
                layer_index=layer_idx,
                target_z=snap.position.z,
                snapshot=snap,
                confidence_score=round(confidence, 3),
            )
            candidates.append(candidate)

        # Ordenar de mayor a menor confianza
        candidates.sort(key=lambda c: c.confidence_score, reverse=True)
        return candidates

    def create_plan(
        self,
        candidate: RecoveryCandidate,
        settings: RecoverySettings,
    ) -> RecoveryPlan:
        """
        Construye un RecoveryPlan editable a partir del candidato seleccionado y las configuraciones.

        Args:
            candidate: Candidato seleccionado para recomenzar.
            settings: Ajustes de recuperación configurados por el usuario.

        Returns:
            Instancia de RecoveryPlan totalmente personalizable.
        """
        snap = candidate.snapshot

        # 1. Determinar temperaturas finales (permitiendo override de usuario)
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

        # 2. Generar Preámbulo de recuperación (Calentamiento, Homing, Modos, Purgado)
        preamble: List[Command] = []

        # A. Establecer Unidades y Modos
        preamble.append(Command(line_number=0, raw_text="G21 ; Metric units", code="G21"))
        pos_mode_code = "G90" if snap.positioning_mode.name == "ABSOLUTE" else "G91"
        preamble.append(Command(line_number=0, raw_text=f"{pos_mode_code} ; Positioning mode", code=pos_mode_code))
        ext_mode_code = "M82" if snap.extrusion_mode.name == "ABSOLUTE" else "M83"
        preamble.append(Command(line_number=0, raw_text=f"{ext_mode_code} ; Extrusion mode", code=ext_mode_code))

        # B. Calentamiento de Cama y Hotend
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

        # C. Estrategia de Homing
        if settings.strategy == RecoveryStrategyType.HOME_XY:
            preamble.append(Command(line_number=0, raw_text="G28 X Y ; Home XY safely", code="G28", parameters={"X": 0.0, "Y": 0.0}))
        elif settings.strategy == RecoveryStrategyType.HOME_XYZ:
            preamble.append(Command(line_number=0, raw_text="G28 ; Home XYZ", code="G28"))

        # D. Ajuste de Ventilador
        if fan_speed > 0:
            preamble.append(Command(line_number=0, raw_text=f"M106 S{int(fan_speed)} ; Restore Fan", code="M106", parameters={"S": fan_speed}))

        # E. Purgado personalizado de filamento (si existe)
        for line in settings.custom_prime_script:
            preamble.append(Command(line_number=0, raw_text=line, code=line.split()[0] if line.strip() else None))

        # F. Reinstaurar coordenada E acumulada
        preamble.append(
            Command(
                line_number=0,
                raw_text=f"G92 E{snap.extruder_position:.4f} ; Restore Extruder E",
                code="G92",
                parameters={"E": snap.extruder_position},
            )
        )

        # 3. Generar Secuencia de Reanudación / Retorno seguro al punto de corte
        resume: List[Command] = []

        # Movimiento de seguridad con Z-hop para evitar colisión con la pieza existente
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

        # Desplazamiento XY al punto objetivo
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

        # Bajar Z a la altura exacta de impresión
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

        # Restaurar Feedrate activo
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