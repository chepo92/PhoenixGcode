"""
Módulo Interpreter de PhoenixGCode.

Responsable de simular o ejecutar virtualmente los comandos de un Document G-code
para reconstruir el estado cinemático y térmico de la impresora 3D en cada paso,
generando un ExecutionTimeline compuesto de ExecutionSnapshots inmutables.
"""

from typing import Dict, Optional
from phoenixgcode.model.command import (
    Command,
    MoveCommand,
    TemperatureCommand,
)
from phoenixgcode.model.document import Document
from phoenixgcode.model.snapshot import (
    ExecutionSnapshot,
    ExecutionTimeline,
    Vector3D,
    PositioningMode,
    ExtrusionMode,
)


class GCodeInterpreter:
    """
    Intérprete sintáctico y cinemático de G-code.

    Procesa secuencialmente los comandos de un Document sin modificarlo
    y construye la historia completa de estados de la máquina (ExecutionTimeline).
    """

    def interpret(self, document: Document) -> ExecutionTimeline:
        """
        Ejecuta virtualmente todo el documento G-code de principio a fin.

        Args:
            document: Documento inmutable con la secuencia de comandos.

        Returns:
            ExecutionTimeline con la secuencia de ExecutionSnapshot de cada comando.
        """
        snapshots = []

        # Estado inicial virtual predeterminado de la máquina 3D
        current_x: float = 0.0
        current_y: float = 0.0
        current_z: float = 0.0
        current_e: float = 0.0
        current_f: float = 0.0
        current_fan: float = 0.0
        hotend_temps: Dict[int, float] = {0: 0.0}
        bed_temp: float = 0.0

        pos_mode: PositioningMode = PositioningMode.ABSOLUTE
        ext_mode: ExtrusionMode = ExtrusionMode.ABSOLUTE
        active_tool: int = 0
        units_in_inches: bool = False
        is_homed: bool = False

        for idx, cmd in enumerate(document):
            # 1. Procesar cambio de modos cinemáticos/unidades
            if cmd.code == "G90":
                pos_mode = PositioningMode.ABSOLUTE
            elif cmd.code == "G91":
                pos_mode = PositioningMode.RELATIVE
            elif cmd.code == "M82":
                ext_mode = ExtrusionMode.ABSOLUTE
            elif cmd.code == "M83":
                ext_mode = ExtrusionMode.RELATIVE
            elif cmd.code == "G20":
                units_in_inches = True
            elif cmd.code == "G21":
                units_in_inches = False
            elif cmd.code == "G28":
                is_homed = True
                # Si G28 especifica ejes, solo esos hacen home; si no, todos a 0.0
                if not cmd.parameters or "X" in cmd.parameters:
                    current_x = 0.0
                if not cmd.parameters or "Y" in cmd.parameters:
                    current_y = 0.0
                if not cmd.parameters or "Z" in cmd.parameters:
                    current_z = 0.0

            # 2. Reset manual de posición (G92)
            elif cmd.code == "G92":
                if "X" in cmd.parameters:
                    current_x = cmd.parameters["X"]
                if "Y" in cmd.parameters:
                    current_y = cmd.parameters["Y"]
                if "Z" in cmd.parameters:
                    current_z = cmd.parameters["Z"]
                if "E" in cmd.parameters:
                    current_e = cmd.parameters["E"]

            # 3. Cambio de herramienta active (T0, T1, etc.)
            elif cmd.code and cmd.code.startswith("T") and cmd.code[1:].isdigit():
                active_tool = int(cmd.code[1:])
                if active_tool not in hotend_temps:
                    hotend_temps[active_tool] = 0.0

            # 4. Comandos de temperatura (M104, M109, M140, M190)
            elif isinstance(cmd, TemperatureCommand):
                if cmd.target_temperature is not None:
                    if cmd.is_bed:
                        bed_temp = cmd.target_temperature
                    else:
                        tool_idx = cmd.tool_index if cmd.tool_index is not None else active_tool
                        hotend_temps[tool_idx] = cmd.target_temperature

            # 5. Control de ventilador (M106, M107)
            elif cmd.code == "M106":
                # M106 S<0-255>
                current_fan = cmd.parameters.get("S", 255.0)
            elif cmd.code == "M107":
                current_fan = 0.0

            # 6. Comandos de Movimiento (G0, G1, G2, G3)
            elif isinstance(cmd, MoveCommand):
                if cmd.f is not None:
                    current_f = cmd.f

                # Actualización de posición cartesiana XYZ
                if pos_mode == PositioningMode.ABSOLUTE:
                    if cmd.x is not None:
                        current_x = cmd.x
                    if cmd.y is not None:
                        current_y = cmd.y
                    if cmd.z is not None:
                        current_z = cmd.z
                else:  # RELATIVE
                    if cmd.x is not None:
                        current_x += cmd.x
                    if cmd.y is not None:
                        current_y += cmd.y
                    if cmd.z is not None:
                        current_z += cmd.z

                # Actualización del motor de extrusión E
                if cmd.e is not None:
                    if ext_mode == ExtrusionMode.ABSOLUTE:
                        current_e = cmd.e
                    else:  # RELATIVE
                        current_e += cmd.e

            # 7. Generar el ExecutionSnapshot correspondiente al final de este comando
            snapshot = ExecutionSnapshot(
                command_index=idx,
                line_number=cmd.line_number,
                position=Vector3D(x=current_x, y=current_y, z=current_z),
                extruder_position=current_e,
                feedrate=current_f,
                fan_speed=current_fan,
                hotend_temperatures=dict(hotend_temps),
                bed_temperature=bed_temp,
                positioning_mode=pos_mode,
                extrusion_mode=ext_mode,
                active_tool=active_tool,
                units_in_inches=units_in_inches,
                is_homed=is_homed,
            )
            snapshots.append(snapshot)

        return ExecutionTimeline(snapshots=tuple(snapshots))