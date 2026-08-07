"""
Pruebas unitarias para el frontend plugin de OctoPrint.
"""

from pathlib import Path
import pytest
from phoenixgcode.api import PhoenixGCodeAPI


class TestOctoPrintPluginFrontend:

    @pytest.fixture
    def sample_gcode(self, tmp_path: Path) -> Path:
        content = (
            "; OctoPrint Test File\n"
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
        file_path = tmp_path / "impresion_octo.gcode"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_octoprint_flow_via_api(self, sample_gcode: Path, tmp_path: Path):
        """Verifica el flujo completo que ejecuta el plugin de OctoPrint usando PhoenixGCodeAPI."""
        # 1. El plugin solicita el plan de recuperación
        plan = PhoenixGCodeAPI.plan_recovery(
            file_path=sample_gcode,
            measured_z=0.4,
            strategy_name="HOME_XY",
        )

        assert plan["candidate"]["target_z"] == 0.4

        # 2. El plugin ejecuta y guarda el nuevo archivo para OctoPrint
        output_path = tmp_path / "impresion_octo_Recovery.gcode"
        generated_file = PhoenixGCodeAPI.execute_recovery(
            input_path=sample_gcode,
            output_path=output_path,
            measured_z=0.4,
            strategy_name="HOME_XY",
        )

        assert Path(generated_file).exists()
        recovered_text = Path(generated_file).read_text(encoding="utf-8")
        assert "PhoenixGCode Recovery File" in recovered_text
        assert "G1 X20 Y20 E1.0" in recovered_text