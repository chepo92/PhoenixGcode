from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, Dict, Optional


class PositioningMode(Enum):
    ABSOLUTE = auto()  # G90
    RELATIVE = auto()  # G91


class ExtrusionMode(Enum):
    ABSOLUTE = auto()  # M82
    RELATIVE = auto()  # M83


@dataclass(frozen=True, slots=True)
class Vector3D:
    """Coordenadas tridimensionales cartesianas (X, Y, Z)."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    """
    Representa el estado interno completo y exacto de la impresora 3D 
    inmediatamente antes o después de la ejecución de una línea de G-code.
    
    Attributes:
        command_index: Índice del comando dentro de Document.commands al que corresponde la foto.
        line_number: Número de línea real dentro del archivo .gcode.
        position: Posición actual en el espacio cartesiano (X, Y, Z) en mm.
        extruder_position: Valor E actual acumulado/absoluto en el motor de extrusión en mm.
        feedrate: Velocidad de movimiento activa en mm/min.
        fan_speed: Velocidad actual del ventilador de capa (0 a 255 o 0% a 100%).
        hotend_temperatures: Mapeo de [índice_herramienta -> temperatura_objetivo_ºC].
        bed_temperature: Temperatura objetivo actual de la cama de impresión en ºC.
        positioning_mode: Modo de coordenadas cartesiano activo (ABSOLUTE/RELATIVE).
        extrusion_mode: Modo de coordenadas del extrusor activo (ABSOLUTE/RELATIVE).
        active_tool: Índice de la herramienta/extrusor actualmente seleccionado (T0, T1...).
        current_layer_index: Número de capa inferido durante la simulación execution.
        units_in_inches: Indica si la impresora opera en pulgadas (G20) o milímetros (G21).
        is_homed: Estado de calibración de origen conocido para los ejes.
    """
    command_index: int
    line_number: int
    position: Vector3D = field(default_factory=Vector3D)
    extruder_position: float = 0.0
    feedrate: float = 0.0
    fan_speed: float = 0.0
    hotend_temperatures: Dict[int, float] = field(default_factory=lambda: {0: 0.0})
    bed_temperature: float = 0.0
    positioning_mode: PositioningMode = PositioningMode.ABSOLUTE
    extrusion_mode: ExtrusionMode = ExtrusionMode.ABSOLUTE
    active_tool: int = 0
    current_layer_index: Optional[int] = None
    units_in_inches: bool = False
    is_homed: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionTimeline:
    """
    Secuencia ordenada e indexada de todos los estados virtuales (ExecutionSnapshot) 
    generados por el Interpreter sobre un Document.
    
    Attributes:
        snapshots: Colección indexada de estados paso a paso por cada comando ejecutable.
    """
    snapshots: Tuple[ExecutionSnapshot, ...] = field(default_factory=tuple)

    def get_snapshot_at_line(self, line_number: int) -> Optional[ExecutionSnapshot]:
        """Obtiene el último snapshot generado para una línea de comando dada."""
        for snap in reversed(self.snapshots):
            if snap.line_number <= line_number:
                return snap
        return None