"""
Índice de capas para PhoenixGCode.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True, slots=True)
class LayerInfo:
    """
    Información relevante sobre una capa individual en la impresión.

    Attributes:
        layer_index: Número ordinal de la capa (0-indexed o 1-indexed según slicer).
        start_line: Número de línea donde inicia la capa en el G-code.
        end_line: Número de línea donde finaliza la capa.
        z_height: Altura Z en la que se desarrolla la capa (mm).
        start_command_index: Índice del primer comando dentro del Document.
        end_command_index: Índice del último comando dentro del Document.
    """
    layer_index: int
    start_line: int
    end_line: int
    z_height: float
    start_command_index: int
    end_command_index: int


@dataclass
class LayerIndex:
    """Índice que mapea números de capa con su información y rangos de líneas."""
    layers: Dict[int, LayerInfo] = field(default_factory=dict)

    def get_layer(self, layer_idx: int) -> Optional[LayerInfo]:
        return self.layers.get(layer_idx)

    @property
    def total_layers(self) -> int:
        return len(self.layers)