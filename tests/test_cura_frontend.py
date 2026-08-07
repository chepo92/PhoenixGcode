"""
Pruebas unitarias para el frontend gráfico de UltiMaker Cura.
"""

from pathlib import Path
import pytest
from phoenixgcode.api import PhoenixGCodeAPI


class TestCuraFrontendIntegration:

    @pytest.fixture
    def sample_gcode(self, tmp_path: Path) -> Path:
        content = (
            "; Cura G-Code Sample\n"
            "G21\n"
            "G90\n"
            "M82\n"
            "M104 S200\n"
            "M140 S60\n"
            "G1 Z0.2 F1200\n"
            "G1 X10 Y10 E0.5\n"
            "G1 Z0.4\n"
            "G1 X20 Y20 E1.0\n"
        )
        file_path = tmp_path / "cura_sample.gcode"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_cura_frontend_invokes_api(self, sample_gcode: Path):
        """
        Simula las llamadas que realiza la extensión de Cura a la API pública.
        """
        # 1. El frontend solicita el plan de recuperación
        plan = PhoenixGCodeAPI.plan_recovery(
            file_path=sample_gcode,
            measured_z=0.4,
            strategy_name="HOME_XY",
            override_hotend_temp=210.0,
        )

        assert plan["candidate"]["target_z"] == 0.4
        assert plan["reconstructed_state"]["hotend_temp"] == 210.0

        # 2. El frontend solicita la generación del archivo final
        out_path = sample_gcode.parent / "cura_sample_Recovery.gcode"
        final_file = PhoenixGCodeAPI.execute_recovery(
            input_path=sample_gcode,
            output_path=out_path,
            measured_z=0.4,
            strategy_name="HOME_XY",
        )

        assert Path(final_file).exists()