"""
Pruebas unitarias para el frontend de línea de comandos (CLI).
"""

from pathlib import Path
import pytest
from typer.testing import CliRunner
from frontends.cli.app import app

runner = CliRunner()


class TestPhoenixCLIFrontend:

    @pytest.fixture
    def sample_gcode(self, tmp_path: Path) -> Path:
        content = (
            "; Phoenix Test File\n"
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
        file_path = tmp_path / "dragon.gcode"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_cli_validate_command(self, sample_gcode: Path):
        result = runner.invoke(app, ["validate", str(sample_gcode)])
        assert result.exit_code == 0
        assert "Sintaxis válida" in result.output

    def test_cli_analyze_command(self, sample_gcode: Path):
        result = runner.invoke(app, ["analyze", str(sample_gcode)])
        assert result.exit_code == 0
        assert "capas detectadas" in result.output

    def test_cli_recover_batch_mode(self, sample_gcode: Path, tmp_path: Path):
        out_file = tmp_path / "dragon_recovered.gcode"
        result = runner.invoke(
            app,
            [
                "recover",
                str(sample_gcode),
                "--z", "0.4",
                "--home", "xy",
                "--output", str(out_file),
                "--batch",
            ],
        )
        assert result.exit_code == 0
        assert out_file.exists()
        assert "PhoenixGCode Recovery File" in out_file.read_text(encoding="utf-8")

    def test_cli_recover_batch_mode_missing_z_error(self, sample_gcode: Path):
        result = runner.invoke(app, ["recover", str(sample_gcode), "--batch"])
        assert result.exit_code != 0
        assert "El parámetro '--z' es obligatorio en modo batch" in result.output

    def test_cli_recover_interactive_wizard_mode(self, sample_gcode: Path, tmp_path: Path):
        out_file = tmp_path / "wizard_out.gcode"
        # Entradas simuladas completas:
        # 1. "0.4\n" -> Ingresar Z medida
        # 2. "\n"    -> Aceptar el candidato [0] en la lista de candidatos
        # 3. "A\n"   -> Aceptar plan en el menú de edición
        # 4. "y\n"   -> Confirmar generación del archivo
        user_inputs = "0.4\n\nA\ny\n"
        result = runner.invoke(
            app,
            ["recover", str(sample_gcode), "--output", str(out_file)],
            input=user_inputs,
        )
        assert result.exit_code == 0, f"Error en la CLI: {result.output}"
        assert out_file.exists()
        assert "PhoenixGCode Recovery File" in out_file.read_text(encoding="utf-8")