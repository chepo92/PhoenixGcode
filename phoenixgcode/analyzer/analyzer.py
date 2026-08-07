"""
Módulo Analyzer de PhoenixGCode.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from phoenixgcode.model.document import Document
from phoenixgcode.model.command import MoveCommand, CommentCommand, CommandType
from phoenixgcode.model.snapshot import ExecutionTimeline, ExecutionSnapshot
from phoenixgcode.analyzer.layer_index import LayerIndex, LayerInfo
from phoenixgcode.analyzer.z_index import ZIndex
from phoenixgcode.analyzer.snapshot_index import SnapshotIndex
from phoenixgcode.analyzer.command_index import CommandIndex


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    layer_index: LayerIndex
    z_index: ZIndex
    snapshot_index: SnapshotIndex
    command_index: CommandIndex
    first_extrusion_command_index: Optional[int] = None
    last_extrusion_command_index: Optional[int] = None
    max_z_height: float = 0.0


class GCodeAnalyzer:
    # Regex para buscar en el texto original (raw_text) que incluye el ';'
    _LAYER_COMMENT_RE = re.compile(
        r";\s*(?:LAYER|layer|BEFORE_LAYER_CHANGE|AFTER_LAYER_CHANGE)[:\s]*(\d+)",
        re.IGNORECASE
    )

    def analyze(self, document: Document, timeline: ExecutionTimeline) -> AnalysisResult:
        layer_idx_map: Dict[int, LayerInfo] = {}
        z_to_cmds: Dict[float, List[int]] = {}
        by_line_snap: Dict[int, ExecutionSnapshot] = {}
        by_cmd_snap: Dict[int, ExecutionSnapshot] = {}
        by_type_cmds: Dict[CommandType, List[int]] = {}
        comment_lines: List[int] = []

        first_extrusion_idx: Optional[int] = None
        last_extrusion_idx: Optional[int] = None
        max_z: float = 0.0

        current_layer_num = 1
        layer_start_cmd_idx = 0
        layer_start_line = document[0].line_number if len(document) > 0 else 1
        current_layer_z = 0.0

        num_commands = len(document)

        for i in range(num_commands):
            cmd = document[i]
            snap = timeline.snapshots[i] if i < len(timeline.snapshots) else None

            if snap:
                by_line_snap[cmd.line_number] = snap
                by_cmd_snap[i] = snap
                current_z = snap.position.z
                if current_z > max_z:
                    max_z = current_z
            else:
                current_z = 0.0

            cmd_type = cmd.command_type
            if cmd_type not in by_type_cmds:
                by_type_cmds[cmd_type] = []
            by_type_cmds[cmd_type].append(i)

            if isinstance(cmd, CommentCommand) or cmd.comment:
                comment_lines.append(cmd.line_number)

            rounded_z = round(current_z, 3)
            if rounded_z not in z_to_cmds:
                z_to_cmds[rounded_z] = []
            z_to_cmds[rounded_z].append(i)

            if isinstance(cmd, MoveCommand) and cmd.e is not None:
                if snap and snap.extruder_position > 0:
                    if first_extrusion_idx is None:
                        first_extrusion_idx = i
                    last_extrusion_idx = i

            detected_layer_change = False
            new_layer_idx = current_layer_num

            # Buscar etiqueta de capa en el raw_text original para asegurar compatibilidad
            if cmd.comment and cmd.raw_text:
                match = self._LAYER_COMMENT_RE.search(cmd.raw_text)
                if match:
                    detected_layer_change = True
                    new_layer_idx = int(match.group(1))

            # Fallback por cambio de Z
            if not detected_layer_change and isinstance(cmd, MoveCommand) and cmd.z is not None:
                if abs(cmd.z - current_layer_z) > 0.001 and first_extrusion_idx is not None:
                    detected_layer_change = True
                    new_layer_idx = current_layer_num + 1

            if detected_layer_change and i > layer_start_cmd_idx:
                prev_end_line = document[i - 1].line_number
                layer_idx_map[current_layer_num] = LayerInfo(
                    layer_index=current_layer_num,
                    start_line=layer_start_line,
                    end_line=prev_end_line,
                    z_height=current_layer_z,
                    start_command_index=layer_start_cmd_idx,
                    end_command_index=i - 1,
                )
                current_layer_num = new_layer_idx
                layer_start_cmd_idx = i
                layer_start_line = cmd.line_number
                current_layer_z = current_z

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