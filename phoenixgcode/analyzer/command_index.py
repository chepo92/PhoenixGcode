"""
Índice clasificatorio de comandos para PhoenixGCode.
"""

from dataclasses import dataclass, field
from typing import Dict, List
from phoenixgcode.model.command import CommandType


@dataclass
class CommandIndex:
    """Índice que clasifica los índices de comandos según su categoría CommandType."""
    by_type: Dict[CommandType, List[int]] = field(default_factory=dict)
    comment_lines: List[int] = field(default_factory=list)

    def get_indices_by_type(self, cmd_type: CommandType) -> List[int]:
        return self.by_type.get(cmd_type, [])