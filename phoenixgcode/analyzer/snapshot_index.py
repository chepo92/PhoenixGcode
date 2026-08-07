"""
Índice de snapshots para PhoenixGCode.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from phoenixgcode.model.snapshot import ExecutionSnapshot


@dataclass
class SnapshotIndex:
    """Índice de acceso rápido O(1) a Snapshots por número de línea o por índice de comando."""
    by_line_number: Dict[int, ExecutionSnapshot] = field(default_factory=dict)
    by_command_index: Dict[int, ExecutionSnapshot] = field(default_factory=dict)

    def get_by_line(self, line_number: int) -> Optional[ExecutionSnapshot]:
        return self.by_line_number.get(line_number)

    def get_by_command_index(self, cmd_index: int) -> Optional[ExecutionSnapshot]:
        return self.by_command_index.get(cmd_index)