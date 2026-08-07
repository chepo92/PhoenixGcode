"""
Componente de formateo de texto y salida visual limpia para la CLI.
"""

from typing import Dict, Any


class CLIFormatter:
    """Maneja la presentación consistente de datos en consola."""

    @staticmethod
    def print_banner() -> None:
        banner = (
            "==========================================================\n"
            " PhoenixGCode Recovery Wizard\n"
            " \"A universal G-code analysis and failed print recovery library\"\n"
            "=========================================================="
        )
        print(banner)

    @staticmethod
    def print_step(message: str) -> None:
        print(f"✓ {message}")

    @staticmethod
    def print_error(message: str) -> None:
        print(f"❌ Error: {message}")

    @staticmethod
    def print_recovery_plan(plan_dto: Dict[str, Any], output_path: str) -> None:
        cand = plan_dto["candidate"]
        state = plan_dto["reconstructed_state"]

        print("\n==========================================================")
        print(" Recovery Plan")
        print("==========================================================")
        print(f"Archivo:            {plan_dto['source_file']}")
        print("\n[Recovery Point]")
        print(f"Línea Original:     {cand['line_number']}")
        print(f"Capa:               #{cand['layer_index']}")
        print(f"Z:                  {cand['target_z']:.3f} mm")
        print(f"Confianza:          {cand['confidence_score'] * 100:.1f}%")

        print("\n[Estado Reconstruido]")
        print(f"Temperatura Hotend: {state['hotend_temp']:.0f}°C")
        print(f"Temperatura Cama:   {state['bed_temp']:.0f}°C")
        print(f"Modo Extrusión:     {state['extrusion_mode']}")
        print(f"Último E:           {state['extruder_e']:.4f}")
        print(f"Fan:                {state['fan_speed']:.0f}")

        print("\n[Estrategia & Output]")
        print(f"Recovery Strategy:  {plan_dto['strategy']}")
        print(f"Output File:        {output_path}")
        print("==========================================================\n")