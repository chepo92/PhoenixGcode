from dataclasses import dataclass, field
from typing import List, Optional
from phoenixgcode.model.command import Command
from phoenixgcode.model.snapshot import ExecutionSnapshot
from phoenixgcode.model.recovery_settings import RecoverySettings


@dataclass(frozen=True, slots=True)
class RecoveryCandidate:
    """
    Punto potencial en el G-code identificado por el Analyzer donde 
    es factible reanudar la impresión.
    
    Attributes:
        line_number: Línea de comando exacta sugerida para continuar.
        layer_index: Número de capa asociada al candidato.
        target_z: Altura Z exacta dentro del archivo G-code.
        snapshot: Estado reconstruido exacto de la impresora en esa línea.
        confidence_score: Valor numérico (0.0 a 1.0) que indica la certeza de coincidencia.
    """
    line_number: int
    layer_index: int
    target_z: float
    snapshot: ExecutionSnapshot
    confidence_score: float = 1.0


@dataclass
class RecoveryPlan:
    """
    Plan intermedio inspeccionable y modificable por el usuario antes 
    de ejecutar la generación del archivo Recovery.gcode final.
    
    Attributes:
        selected_candidate: Candidato de recuperación seleccionado para recomenzar.
        reconstructed_snapshot: Estado térmico y cinemático que se debe restaurar.
        preamble_commands: Lista de comandos G-code a insertar antes del corte (purgado, temp, home).
        resume_commands: Primeros comandos de movimiento para retomar la geometría sin colisiones.
        settings_used: Copia de los ajustes de recuperación utilizados para generar el plan.
    """
    selected_candidate: RecoveryCandidate
    reconstructed_snapshot: ExecutionSnapshot
    preamble_commands: List[Command] = field(default_factory=list)
    resume_commands: List[Command] = field(default_factory=list)
    settings_used: Optional[RecoverySettings] = None