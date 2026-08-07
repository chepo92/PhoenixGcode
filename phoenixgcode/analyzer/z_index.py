"""
Índice de alturas Z para PhoenixGCode.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ZIndex:
    """
    Índice que mapea alturas físicas Z (mm) con los números de línea 
    o índices de comando correspondientes.
    """
    # Mapeo de Z (redondeado a 3 decimales) -> lista de índices de comandos en Document
    z_to_command_indices: Dict[float, List[int]] = field(default_factory=dict)
    sorted_z_heights: List[float] = field(default_factory=list)

    def get_commands_at_z(self, z_height: float, tolerance: float = 0.001) -> List[int]:
        """Obtiene los índices de comandos ejecutados a una altura Z determinada dentro de una tolerancia."""
        rounded_z = round(z_height, 3)
        if rounded_z in self.z_to_command_indices:
            return self.z_to_command_indices[rounded_z]
        
        # Búsqueda por tolerancia
        result = []
        for z, indices in self.z_to_command_indices.items():
            if abs(z - z_height) <= tolerance:
                result.extend(indices)
        return result

    def find_closest_z(self, target_z: float) -> Optional[float]:
        """Encuentra la altura Z válida registrada más cercana al valor objetivo."""
        if not self.sorted_z_heights:
            return None
        return min(self.sorted_z_heights, key=lambda z: abs(z - target_z))