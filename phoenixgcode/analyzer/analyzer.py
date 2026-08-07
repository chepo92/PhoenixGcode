"""
Módulo Analyzer de PhoenixGCode.

Responsable de inspeccionar un Document y su ExecutionTimeline para generar
índices de acceso rápido y extraer metadatos analíticos clave (capas, movimiento inicial,
última extrusión, etc.).
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from phoenixgcode.model.document import Document
from phoenixgcode.model.command import MoveCommand, CommentCommand, CommandType
from phoenixgcode.model.snapshot import ExecutionTimeline, ExecutionSnapshot
from phoenixgcode.analyzer.layer_index import LayerIndex, LayerInfo
from phoenixgcode.analyzer.z_index import ZIndex
from phoenixgcode.analyzer.snapshot_index import SnapshotIndex
from phoenixgcode.analyzer.command_index import CommandIndex


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """
    Contenedor principal con todos los índices y metadatos calculados durante el análisis.
    
    Attributes:
        layer_index: Índice de capas e información de rangos.
        z_index: Índice de alturas Z.
        snapshot_index: Mapeo O(1) de snapshots por línea y por comando.
        command_index: Clasificación de comandos por tipo.
        first_extrusion_command_index: Índice del primer movimiento que extruye filamento.
        last_extrusion_command_index: Índice del último movimiento que extruye filamento.
        max_z_height: Altura máxima Z alcanzada en la impresión.
    """
    layer_index: LayerIndex
    z_index: ZIndex
    snapshot_index: SnapshotIndex
    command_index: CommandIndex
    first_extrusion_command_index: Optional[int] = None
    last_extrusion_command_index: Optional[int] = None
    max_z_height: float = 0.0


class GCodeAnalyzer:
    """
    Analizador estático e interpretativo de G-code.

    Realiza una sola pasada sobre el Document y el ExecutionTimeline para 
    poblar todos los índices analíticos requeridos.
    """

    # Expresiones regulares para detectar etiquetas de capa de slicers populares (Cura, Prusa, Orca, etc.)
    _LAYER_COMMENT_RE = re.compile(
        r";\s*(?:LAYER|layer|BEFORE_LAYER_CHANGE|AFTER_LAYER_CHANGE)[:\s]*(\d+)",
        re.IGNORECASE
    )

    def analyze(self, document: Document, timeline: ExecutionTimeline) -> AnalysisResult:
        """
        Analiza un Document y su ExecutionTimeline construyendo los índices en una sola pasada.

        Args:
            document: El documento G-code parseado.
            timeline: La línea de tiempo de ejecución simula por Interpreter.

        Returns:
            AnalysisResult con todos los índices construidos y metadatos clave.
        """
        layer_idx_map: Dict[int, LayerInfo] = {}
        z_to_cmds: Dict[float, List[int]] = {}
        by_line_snap: Dict[int, ExecutionSnapshot] = {}
        by_cmd_snap: Dict[int, ExecutionSnapshot] = {}
        by_type_cmds: Dict[CommandType, List[int]] = {}
        comment_lines: List[int] = []

        first_extrusion_idx: Optional[int] = None
        last_extrusion_idx: Optional[int] = None
        max_z: float = 0.0

        current_layer_num = 0
        layer_start_cmd_idx = 0
        layer_start_line = document[0].line_number if len(document) > 0 else 1
        current_layer_z = 0.0

        num_commands = len(document)

        for i in range(num_commands):
            cmd = document[i]
            snap = timeline.snapshots[i] if i < len(timeline.snapshots) else None

            # 1. Poblar SnapshotIndex
            if snap:
                by_line_snap[cmd.line_number] = snap
                by_cmd_snap[i] = snap
                current_z = snap.position.z
                if current_z > max_z:
                    max_z = current_z
            else:
                current_z = 0.0

            # 2. Poblar CommandIndex
            cmd_type = cmd.command_type
            if cmd_type not in by_type_cmds:
                by_type_cmds[cmd_type] = []
            by_type_cmds[cmd_type].append(i)

            if isinstance(cmd, CommentCommand) or cmd.comment:
                comment_lines.append(cmd.line_number)

            # 3. Poblar ZIndex
            rounded_z = round(current_z, 3)
            if rounded_z not in z_to_cmds:
                z_to_cmds[rounded_z] = []
            z_to_cmds[rounded_z].append(i)

            # 4. Detectar Primera y Última Extrusión
            if isinstance(cmd, MoveCommand) and cmd.e is not None:
                # Si el estado muestra incremento real de E o extrusión activa
                if snap and snap.extruder_position > 0:
                    if first_extrusion_idx is None:
                        first_extrusion_idx = i
                    last_extrusion_idx = i

            # 5. Detección de Capas (Layer Detection)
            detected_layer_change = False
            new_layer_idx = current_layer_num

            # A. Detección por comentario explícito del Slicer
            if cmd.comment:
                match = self._LAYER_COMMENT_RE.search(cmd.comment)
                if match:
                    detected_layer_change = True
                    new_layer_idx = int(match.group(1))

            # B. Fallback por cambio de Z en movimiento
            if not detected_layer_change and isinstance(cmd, MoveCommand) and cmd.z is not None:
                if abs(cmd.z - current_layer_z) > 0.001 and first_extrusion_idx is not None:
                    detected_layer_change = True
                    new_layer_idx = current_layer_num + 1

            if detected_layer_change and i > layer_start_cmd_idx:
                # Cerrar capa anterior
                prev_end_line = document[i - 1].line_number
                layer_idx_map[current_layer_num] = LayerInfo(
                    layer_index=current_layer_num,
                    start_line=layer_start_line,
                    end_line=prev_end_line,
                    z_height=current_layer_z,
                    start_command_index=layer_start_cmd_idx,
                    end_command_index=i - 1,
                )
                # Iniciar nueva capa
                current_layer_num = new_layer_idx
                layer_start_cmd_idx = i
                layer_start_line = cmd.line_number
                current_layer_z = current_z

        # Registrar la última capa inconclusa al final del bucle
        if num_commands > 0:
            last_cmd = document[num_commands - 1]
            layer_idx_map[current_layer_num] = LayerInfo(
                layer_index=current_layer_num,
                start_line=layer_start_line,
                end_line=last_cmd.line_number,
                z_height=current_layer_z,
                start_command_index=layer_start_cmd_idx,
                end_command_index=num_commands - 1,
            )

        sorted_zs = sorted(z_to_cmds.keys())

        return AnalysisResult(
            layer_index=LayerIndex(layers=layer_idx_map),
            z_index=ZIndex(z_to_command_indices=z_to_cmds, sorted_z_heights=sorted_zs),
            snapshot_index=SnapshotIndex(by_line_number=by_line_snap, by_command_index=by_cmd_snap),
            command_index=CommandIndex(by_type=by_type_cmds, comment_lines=comment_lines),
            first_extrusion_command_index=first_extrusion_idx,
            last_extrusion_command_index=last_extrusion_idx,
            max_z_height=max_z,
        )