from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List


class RecoveryStrategyType(Enum):
    MANUAL_POSITION = auto()  # Ejes Z levantados manualmente, Home solo en XY
    HOME_XY = auto()           # Re-home XY con cuidado de no golpear la pieza
    HOME_XYZ = auto()          # Re-home total (requiere espacio despejado fuera de cama)
    CUSTOM_SCRIPT = auto()     # Delegado enteramente a script de usuario


@dataclass
class RecoverySettings:
    """
    Parámetros configurables proporcionados por el usuario o inferidos 
    por el analizador para guiar el proceso de recuperación.
    
    Attributes:
        measured_z: Altura Z real medida físicamente en la pieza impresa (en mm).
        z_tolerance: Tolerancia de búsqueda para vincular la medida Z a una capa (en mm).
        strategy: Estrategia elegida para re-inicializar el estado de cinemática de la impresora.
        override_bed_temp: Temperatura personalizada para la cama. Si es None, usa la inferida.
        override_hotend_temp: Temperatura personalizada para el hotend. Si es None, usa la inferida.
        override_fan_speed: Velocidad de ventilador personalizada. Si es None, usa la inferida.
        custom_prime_script: Lista de líneas G-code personalizadas para purgar el extrusor.
        retraction_on_pause: Distancia a retraer filamento antes de levantar el cabezal (mm).
        z_hop_distance: Distancia de seguridad para levantar el cabezal durante el viaje inicial (mm).
    """
    measured_z: float
    z_tolerance: float = 0.1
    strategy: RecoveryStrategyType = RecoveryStrategyType.HOME_XY
    override_bed_temp: Optional[float] = None
    override_hotend_temp: Optional[float] = None
    override_fan_speed: Optional[float] = None
    custom_prime_script: List[str] = field(default_factory=list)
    retraction_on_pause: float = 2.0
    z_hop_distance: float = 10.0