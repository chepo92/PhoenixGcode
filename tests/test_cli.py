"""
Pruebas unitarias para la interfaz de línea de comandos (CLI) de PhoenixGCode.
"""

from pathlib import Path
import pytest
from phoenixgcode.cli.main import main


class TestPhoenixCLI:

    @pytest.fixture
    def sample_gcode(self, tmp_path: Path) -> Path:
        """Crea un archivo G-code simple para pruebas de integración CLI."""
        gcode_content = (
            "; PhoenixGCode Test File\n"
            "G21\n"
            "G90\n"
            "M82\n"
            "M104 S200\n"
            "M140 S60\n"
            "G1 Z0.2 F1200\n"
            "G1 X10 Y10 E0.5\n"
            "G1 Z0.4\n"
            "G1 X20 Y20 E1.0\n"
            "G1 X30 Y30 E1.5\n"
        )
        file_path = tmp_path / "pieza_test.gcode"
        file_path.write_text(gcode_content, encoding="utf-8")
        return file_path

    def test_cli_recover_non_interactive(self, sample_gcode: Path, monkeypatch, capsys):
        """Verifica que 'phoenix recover' genere el archivo Recovery en modo no interactivo."""
        output_file = sample_gcode.parent / "pieza_test_Recovery.gcode"

        # Simular argumentos de la CLI: phoenix recover pieza_test.gcode -z 0.4 --non-interactive
        test_args = [
            "phoenix",
            "recover",
            str(sample_gcode),
            "-z", "0.4",
            "--non-interactive",
        ]
        monkeypatch.setattr("sys.argv", test_args)

        main()

        captured = capsys.readouterr()
        assert "Proceso finalizado con éxito" in captured.out
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "PhoenixGCode Recovery File" in content
        assert "G1 X20 Y20 E1.0" in content