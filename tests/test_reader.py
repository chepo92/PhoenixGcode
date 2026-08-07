"""
Pruebas unitarias para el módulo Reader de PhoenixGCode.

Para ejecutar las pruebas con el soporte de detección de encoding, asegúrate de tener instalados los paquetes requeridos:
pip install chardet pytest

pytest tests/test_reader.py -v

"""

from pathlib import Path
import pytest
from phoenixgcode.reader.reader import GCodeReader


@pytest.fixture
def create_temp_gcode(tmp_path: Path):
    """Fixture auxiliar para generar archivos G-code temporales con distinto contenido y encoding."""
    def _factory(filename: str, content: str, encoding: str = "utf-8", write_bytes: bytes = None) -> Path:
        file_path = tmp_path / filename
        if write_bytes is not None:
            file_path.write_bytes(write_bytes)
        else:
            file_path.write_text(content, encoding=encoding)
        return file_path

    return _factory


class TestGCodeReader:

    def test_file_not_found(self):
        """Verifica que se lance FileNotFoundError si el archivo no existe."""
        with pytest.raises(FileNotFoundError):
            GCodeReader("archivo_inexistente.gcode")

    def test_directory_provided_raises_error(self, tmp_path: Path):
        """Verifica que se lance IsADirectoryError si se pasa una ruta de carpeta."""
        with pytest.raises(IsADirectoryError):
            GCodeReader(tmp_path)

    def test_detect_encoding_utf8(self, create_temp_gcode):
        """Verifica la detección correcta de archivos en UTF-8 estándar."""
        content = "; PhoenixGCode Test File\nG21 ; Metric values\nG90 ; Absolute positioning\n"
        gcode_file = create_temp_gcode("test_utf8.gcode", content, encoding="utf-8")

        reader = GCodeReader(gcode_file)
        detected = reader.detect_encoding()

        assert detected == "utf-8"

    def test_detect_encoding_utf8_bom(self, create_temp_gcode):
        """Verifica la detección de la firma UTF-8 con BOM."""
        raw_bytes = b"\xef\xbb\xbf; Header with BOM\nG1 X10 Y20\n"
        gcode_file = create_temp_gcode("test_bom.gcode", "", write_bytes=raw_bytes)

        reader = GCodeReader(gcode_file)
        detected = reader.detect_encoding()

        assert detected == "utf-8-sig"

    def test_detect_encoding_latin1(self, create_temp_gcode):
        """Verifica la lectura de caracteres especiales codificados en ISO-8859-1 / Latin-1."""
        content = "; Comentario con caracteres especiales: Impresión de configuración año 2026\nG1 X5.0\n"
        gcode_file = create_temp_gcode("test_latin1.gcode", content, encoding="iso-8859-1")

        reader = GCodeReader(gcode_file)
        lines = list(reader.read_lines())

        assert len(lines) == 2
        assert "Impresión" in lines[0][1]

    def test_streaming_read_lines(self, create_temp_gcode):
        """Verifica que las líneas se lean secuencialmente manteniendo los números de línea y texto intactos."""
        gcode_lines = [
            "; Layer 1",
            "M104 S200",
            "M109 S200",
            "G28",
            "G1 Z0.2 F1200",
            "G1 X10 Y10 E0.5"
        ]
        content = "\n".join(gcode_lines) + "\n"
        gcode_file = create_temp_gcode("test_stream.gcode", content)

        reader = GCodeReader(gcode_file)
        stream_result = list(reader.read_lines())

        assert len(stream_result) == len(gcode_lines)

        for idx, (line_num, line_text) in enumerate(stream_result, start=1):
            assert line_num == idx
            assert line_text == gcode_lines[idx - 1]

    def test_reader_does_not_interpret_gcode(self, create_temp_gcode):
        """
        Verifica la Regla de Oro: Reader NO interpreta G-code.
        Conserva errores sintácticos, comentarios y comandos sin modificar.
        """
        content = "INVALID_GCODE_LINE\nG1 X10 Y20 ; comment\n\n; pure comment"
        gcode_file = create_temp_gcode("raw_test.gcode", content)

        reader = GCodeReader(gcode_file)
        lines = [text for _, text in reader.read_lines()]

        assert lines[0] == "INVALID_GCODE_LINE"
        assert lines[1] == "G1 X10 Y20 ; comment"
        assert lines[2] == ""
        assert lines[3] == "; pure comment"

    def test_empty_file(self, create_temp_gcode):
        """Verifica el comportamiento correcto ante un archivo vacío."""
        gcode_file = create_temp_gcode("empty.gcode", "")
        reader = GCodeReader(gcode_file)

        lines = list(reader.read_lines())
        assert len(lines) == 0