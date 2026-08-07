from pathlib import Path
import pytest
from phoenixgcode.api import PhoenixGCodeAPI

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"

@pytest.mark.skipif(not SAMPLES_DIR.exists(), reason="Carpeta samples/ no encontrada")
def test_e2e_recovery_with_sample_files(tmp_path):
    sample_files = list(SAMPLES_DIR.glob("*.gcode"))
    assert len(sample_files) > 0, "No se encontraron archivos .gcode en /samples"

    for sample_file in sample_files:
        # 1. Analizar archivo real
        analysis = PhoenixGCodeAPI.analyze_file(sample_file)
        assert analysis["total_lines"] > 0
        assert len(analysis["available_z_heights"]) > 0

        # Seleccionar una altura Z intermedia real del archivo
        target_z = analysis["available_z_heights"][len(analysis["available_z_heights"]) // 2]

        # 2. Planificar recuperación
        plan = PhoenixGCodeAPI.plan_recovery(
            file_path=sample_file,
            measured_z=target_z,
            strategy_name="HOME_XY"
        )

        candidates = plan["candidates"]
        assert len(candidates) > 0, f"No se encontraron candidatos para {sample_file.name} en Z={target_z}"

        # Validar que los números de capa sean distintos de cero
        first_candidate = candidates[0]
        assert first_candidate["layer_index"] > 0, (
            f"Fallo en {sample_file.name}: layer_index es 0 para Z={target_z}"
        )

        # 3. Ejecutar recuperación completa
        output_gcode = tmp_path / f"recovery_{sample_file.name}"
        result_path = PhoenixGCodeAPI.execute_recovery(
            input_path=sample_file,
            output_path=output_gcode,
            measured_z=target_z,
            candidate_index=0,
            strategy_name="HOME_XY"
        )

        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0