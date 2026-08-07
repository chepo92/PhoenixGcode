"""
Frontend Plugin de OctoPrint para PhoenixGCode.

Ubicación: frontends/octoprint/octoprint_phoenix.py

Responsabilidades:
- Integración con la interfaz Web y el File System de OctoPrint.
- Exponer endpoints REST para la UI.
- Delegar el 100% del análisis, planificación y generación a PhoenixGCodeAPI.
"""

from pathlib import Path
import flask
import octoprint.plugin
from octoprint.filemanager import FileDestinations

# Importación exclusiva de la API pública de PhoenixGCode
from phoenixgcode.api import PhoenixGCodeAPI


class PhoenixGCodeOctoPrintPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
):
    """
    Plugin de OctoPrint que actúa como puente de UI/API Gateway hacia PhoenixGCode.
    """

    def on_after_startup(self):
        self._logger.info("PhoenixGCode OctoPrint Frontend activado correctamente.")

    # --- Configuración de la API REST del Plugin ---

    def get_api_commands(self):
        """Define las acciones disponibles para llamados AJAX desde la UI Web."""
        return dict(
            list_gcode_files=[],
            plan_recovery=["target_file", "measured_z"],
            execute_recovery=["target_file", "measured_z"],
        )

    def on_api_command(self, command, data):
        """Maneja las peticiones de la API expuestas al cliente Web."""
        try:
            if command == "list_gcode_files":
                return self._handle_list_gcode_files()

            elif command == "plan_recovery":
                return self._handle_plan_recovery(data)

            elif command == "execute_recovery":
                return self._handle_execute_recovery(data)

        except Exception as e:
            self._logger.error(f"Error en PhoenixGCode OctoPrint Plugin: {str(e)}", exc_info=True)
            return flask.jsonify({"status": "error", "message": str(e)}), 400

    # --- Manejadores delegados a PhoenixGCodeAPI ---

    def _handle_list_gcode_files(self):
        """Detecta los archivos .gcode almacenados en el File Manager local de OctoPrint."""
        files_dict = self._file_manager.list_files(target=FileDestinations.LOCAL)
        gcode_files = []

        def _extract_files(tree):
            for key, val in tree.items():
                if val.get("type") == "machinecode":
                    gcode_files.append({
                        "name": val.get("name"),
                        "path": val.get("path"),
                        "size": val.get("size"),
                    })
                elif val.get("type") == "folder" and "children" in val:
                    _extract_files(val["children"])

        if "local" in files_dict:
            _extract_files(files_dict["local"])

        return flask.jsonify({"status": "success", "files": gcode_files})

    def _handle_plan_recovery(self, data):
        """Obtiene un borrador de RecoveryPlan invocando PhoenixGCodeAPI."""
        target_file = data.get("target_file")
        measured_z = float(data.get("measured_z", 0.0))
        strategy = data.get("strategy", "HOME_XY")
        override_hotend = data.get("override_hotend_temp")
        override_bed = data.get("override_bed_temp")

        # Resolver la ruta física del archivo dentro de OctoPrint
        abs_path = self._file_manager.path_on_disk(FileDestinations.LOCAL, target_file)

        # Delegar 100% del análisis a PhoenixGCodeAPI
        plan_dto = PhoenixGCodeAPI.plan_recovery(
            file_path=abs_path,
            measured_z=measured_z,
            strategy_name=strategy,
            override_hotend_temp=float(override_hotend) if override_hotend else None,
            override_bed_temp=float(override_bed) if override_bed else None,
        )

        return flask.jsonify({"status": "success", "plan": plan_dto})

    def _handle_execute_recovery(self, data):
        """
        Compila el nuevo archivo Recovery.gcode usando PhoenixGCodeAPI 
        y lo guarda en la biblioteca de OctoPrint.
        """
        target_file = data.get("target_file")
        measured_z = float(data.get("measured_z", 0.0))
        strategy = data.get("strategy", "HOME_XY")
        override_hotend = data.get("override_hotend_temp")
        override_bed = data.get("override_bed_temp")

        # 1. Ruta del archivo original
        input_abs_path = Path(self._file_manager.path_on_disk(FileDestinations.LOCAL, target_file))

        # 2. Definir nombre del nuevo archivo en OctoPrint
        output_filename = f"{input_abs_path.stem}_Recovery{input_abs_path.suffix}"
        output_abs_path = input_abs_path.parent / output_filename

        # 3. Invocar la biblioteca PhoenixGCode para transformar y escribir
        generated_path = PhoenixGCodeAPI.execute_recovery(
            input_path=input_abs_path,
            output_path=output_abs_path,
            measured_z=measured_z,
            strategy_name=strategy,
            override_hotend_temp=float(override_hotend) if override_hotend else None,
            override_bed_temp=float(override_bed) if override_bed else None,
        )

        # 4. Registrar/notificar el nuevo archivo al FileManager de OctoPrint
        relative_path_in_octoprint = str(Path(target_file).parent / output_filename)
        self._file_manager.add_file(
            destination=FileDestinations.LOCAL,
            path=relative_path_in_octoprint,
            file_object=generated_path,
            allow_overwrite=True,
        )

        return flask.jsonify({
            "status": "success",
            "recovery_file_name": output_filename,
            "octoprint_path": relative_path_in_octoprint,
        })

    # --- Integración de UI y Assets ---

    def get_assets(self):
        return dict(
            js=["js/phoenixgcode_octoprint.js"],
            css=["css/phoenixgcode_octoprint.css"]
        )

    def get_template_configs(self):
        return [
            dict(type="tab", name="Phoenix Recovery", template="phoenixgcode_octoprint_tab.jinja2")
        ]


__plugin_name__ = "PhoenixGCode Recovery Plugin"
__plugin_pythoncompat__ = ">=3.11,<4"
__plugin_implementation__ = PhoenixGCodeOctoPrintPlugin()