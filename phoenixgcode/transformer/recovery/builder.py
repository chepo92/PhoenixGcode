"""
Módulo Recovery Builder de PhoenixGCode.

Responsable de tomar un RecoveryPlan y RecoverySettings para compilar
un nuevo objeto Document inmutable listo para ser enviado al Writer.
No realiza operaciones de I/O ni escribe en disco.
"""

from typing import List
from phoenixgcode.model.command import Command, MoveCommand, CommentCommand
from phoenixgcode.model.document import Document
from phoenixgcode.model.recovery_plan import RecoveryPlan
from phoenixgcode.model.recovery_settings import RecoverySettings, RecoveryStrategyType


class RecoveryBuilder:
    """
    Ensamblador del Document de recuperación.

    Aplica la estrategia elegida y combina los comandos de preámbulo,
    movimientos de reanudación y la secuencia de comandos restante del G-code original.
    """

    def build_document(
        self,
        original_document: Document,
        plan: RecoveryPlan,
        settings: RecoverySettings,
    ) -> Document:
        """
        Construye el nuevo Document de recuperación.

        Args:
            original_document: El Document G-code completo original.
            plan: El RecoveryPlan (puede haber sido modificado por el usuario).
            settings: Los ajustes de recuperación activos.

        Returns:
            Un nuevo objeto Document con la secuencia completa formateada.
        """
        new_commands: List[Command] = []

        # 1. Encabezado e identificación de PhoenixGCode
        new_commands.append(
            CommentCommand(
                line_number=0,
                raw_text="; ==========================================================",
                clean_text=" ==========================================================",
            )
        )
        new_commands.append(
            CommentCommand(
                line_number=0,
                raw_text="; PhoenixGCode Recovery File",
                clean_text=" PhoenixGCode Recovery File",
            )
        )
        new_commands.append(
            CommentCommand(
                line_number=0,
                raw_text=f"; Resuming from Original Line: {plan.selected_candidate.line_number} | Target Z: {plan.selected_candidate.target_z:.3f}mm",
                clean_text=f" Resuming from Original Line: {plan.selected_candidate.line_number} | Target Z: {plan.selected_candidate.target_z:.3f}mm",
            )
        )
        new_commands.append(
            CommentCommand(
                line_number=0,
                raw_text=f"; Strategy: {settings.strategy.name}",
                clean_text=f" Strategy: {settings.strategy.name}",
            )
        )
        new_commands.append(
            CommentCommand(
                line_number=0,
                raw_text="; ==========================================================",
                clean_text=" ==========================================================",
            )
        )

        # 2. Inyección de Preámbulo (Configuraciones, Temperaturas, Homing base)
        new_commands.extend(plan.preamble_commands)

        # 3. Aplicación específica de la Estrategia de Recuperación (Recovery Strategy)
        strategy_commands = self._build_strategy_commands(plan, settings)
        new_commands.extend(strategy_commands)

        # 4. Inyección de Secuencia de Reanudación / Retorno al punto de impresión
        new_commands.extend(plan.resume_commands)

        new_commands.append(
            CommentCommand(
                line_number=0,
                raw_text="; --- RESUMING ORIGINAL G-CODE EXECUTION ---",
                clean_text=" --- RESUMING ORIGINAL G-CODE EXECUTION ---",
            )
        )

        # 5. Copiar la subsecuencia restante de comandos desde el punto candidato seleccionado
        candidate_line_num = plan.selected_candidate.line_number
        start_index = 0

        # Ubicar el índice del comando correspondiente a la línea elegida
        for idx, cmd in enumerate(original_document):
            if cmd.line_number >= candidate_line_num:
                start_index = idx
                break

        remaining_commands = list(original_document.commands[start_index:])
        new_commands.extend(remaining_commands)

        # Devuelve un nuevo Document inmutable
        return Document(commands=tuple(new_commands))

    def _build_strategy_commands(
        self,
        plan: RecoveryPlan,
        settings: RecoverySettings,
    ) -> List[Command]:
        """Genera comandos tácticos según la estrategia de recuperación configurada."""
        strategy_cmds: List[Command] = []

        if settings.strategy == RecoveryStrategyType.MANUAL_POSITION:
            # En posición manual, se asume que el usuario alineó físicamente el cabezal
            snap = plan.reconstructed_snapshot
            strategy_cmds.append(
                CommentCommand(
                    line_number=0,
                    raw_text="; Strategy: MANUAL_POSITION - Setting current coordinates without homing",
                    clean_text=" Strategy: MANUAL_POSITION - Setting current coordinates without homing",
                )
            )
            strategy_cmds.append(
                Command(
                    line_number=0,
                    raw_text=f"G92 X{snap.position.x:.3f} Y{snap.position.y:.3f} Z{snap.position.z:.3f}",
                    code="G92",
                    parameters={
                        "X": snap.position.x,
                        "Y": snap.position.y,
                        "Z": snap.position.z,
                    },
                )
            )

        elif settings.strategy == RecoveryStrategyType.HOME_XY:
            strategy_cmds.append(
                CommentCommand(
                    line_number=0,
                    raw_text="; Strategy: HOME_XY - Homing XY only to preserve current Z position",
                    clean_text=" Strategy: HOME_XY - Homing XY only to preserve current Z position",
                )
            )
            # Definir Z actual con G92 para evitar despejes erróneos de Z en firmware
            target_z = plan.selected_candidate.target_z
            strategy_cmds.append(
                Command(
                    line_number=0,
                    raw_text=f"G92 Z{target_z:.3f}",
                    code="G92",
                    parameters={"Z": target_z},
                )
            )

        elif settings.strategy == RecoveryStrategyType.HOME_XYZ:
            strategy_cmds.append(
                CommentCommand(
                    line_number=0,
                    raw_text="; Strategy: HOME_XYZ - Standard full homing procedure",
                    clean_text=" Strategy: HOME_XYZ - Standard full homing procedure",
                )
            )

        elif settings.strategy == RecoveryStrategyType.CUSTOM_SCRIPT:
            strategy_cmds.append(
                CommentCommand(
                    line_number=0,
                    raw_text="; Strategy: CUSTOM_SCRIPT - Executing user recovery macro",
                    clean_text=" Strategy: CUSTOM_SCRIPT - Executing user recovery macro",
                )
            )
            for raw_line in settings.custom_prime_script:
                strategy_cmds.append(
                    Command(
                        line_number=0,
                        raw_text=raw_line,
                        code=raw_line.split()[0] if raw_line.strip() else None,
                    )
                )

        return strategy_cmds