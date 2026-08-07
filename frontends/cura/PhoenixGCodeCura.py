"""
Frontend Gráfico Oficial de PhoenixGCode para UltiMaker Cura.

Registra la herramienta en el menú de Cura y despliega el diálogo gráfico
consumiendo EXCLUSIVAMENTE la API pública de PhoenixGCode.
"""

import os
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, pyqtProperty
from PyQt5.QtWidgets import QFileDialog

from UM.Extension import Extension
from UM.Application import Application
from UM.PluginRegistry import PluginRegistry

# Importación de la API pública de la biblioteca PhoenixGCode
from phoenixgcode.api import PhoenixGCodeAPI


class PhoenixGCodeCuraExtension(QObject, Extension):
    """
    Extensión gráfica de Cura para PhoenixGCode.
    Actúa únicamente como puente entre la UI en QML/PyQt y PhoenixGCodeAPI.
    """

    # Señales para notificar a la interfaz QML cambios en el estado del plan
    planUpdated = pyqtSignal()
    statusMessageChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        Extension.__init__(self)

        self._plugin_path = PluginRegistry.getInstance().getPluginPath(self.getPluginId())
        self._dialog = None

        # Propiedades vinculadas a la interfaz visual (QML)
        self._selected_file = ""
        self._measured_z = 0.0
        self._strategy = "HOME_XY"
        self._override_hotend = 0.0
        self._override_bed = 0.0

        # Datos devueltos por la API de PhoenixGCode
        self._candidate_line = 0
        self._candidate_z = 0.0
        self._confidence_score = 0.0
        self._status_message = "Seleccione un archivo .gcode e ingrese la altura Z."

        # Registrar el comando en la barra de menú de Cura
        self.addMenuItem("Recover Failed Print...", self.show_dialog)

    def show_dialog(self):
        """Crea y muestra la ventana de diálogo QML al hacer clic en el menú."""
        if not self._dialog:
            qml_path = os.path.join(self._plugin_path, "PhoenixGCodeDialog.qml")
            self._dialog = Application.getInstance().createQmlComponent(qml_path, {"manager": self})
        if self._dialog:
            self._dialog.show()

    # --- Métodos y Slots expuestos a la UI (QML) ---

    @pyqtSlot()
    def browseFile(self):
        """Abre el explorador de archivos nativo del sistema operativo."""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Seleccionar archivo G-code interrumpido",
            "",
            "Archivos G-Code (*.gcode *.g)"
        )
        if file_path:
            self._selected_file = file_path
            self._status_message = f"Archivo cargado: {os.path.basename(file_path)}"
            self.statusMessageChanged.emit(self._status_message)
            self.planUpdated.emit()

    @pyqtSlot(float, str, float, float)
    def calculateRecoveryPlan(self, measured_z, strategy, hotend_temp, bed_temp):
        """
        Solicita a PhoenixGCodeAPI que analice el archivo y genere un Recovery Plan.
        NO procesa G-code; delega 100% a la biblioteca.
        """
        if not self._selected_file or not os.path.exists(self._selected_file):
            self._status_message = "Error: Primero seleccione un archivo G-code válido."
            self.statusMessageChanged.emit(self._status_message)
            return

        self._measured_z = measured_z
        self._strategy = strategy
        self._override_hotend = hotend_temp if hotend_temp > 0 else None
        self._override_bed = bed_temp if bed_temp > 0 else None

        try:
            # Llama a la API Pública de PhoenixGCode
            plan = PhoenixGCodeAPI.plan_recovery(
                file_path=self._selected_file,
                measured_z=measured_z,
                strategy_name=strategy,
                override_hotend_temp=self._override_hotend,
                override_bed_temp=self._override_bed,
            )

            cand = plan["candidate"]
            self._candidate_line = cand["line_number"]
            self._candidate_z = cand["target_z"]
            self._confidence_score = cand["confidence_score"] * 100.0

            self._status_message = f"Plan generado: Corte en línea {self._candidate_line} (Z={self._candidate_z:.3f}mm)."
            self.statusMessageChanged.emit(self._status_message)
            self.planUpdated.emit()

        except Exception as e:
            self._status_message = f"Error al generar plan: {str(e)}"
            self.statusMessageChanged.emit(self._status_message)

    @pyqtSlot()
    def generateRecoveryFile(self):
        """
        Solicita a PhoenixGCodeAPI que genere el archivo final Recovery.gcode.
        """
        if not self._selected_file:
            return

        base_name, ext = os.path.splitext(self._selected_file)
        default_out = f"{base_name}_Recovery{ext}"

        output_path, _ = QFileDialog.getSaveFileName(
            None,
            "Guardar archivo Recovery.gcode",
            default_out,
            "Archivos G-Code (*.gcode *.g)"
        )

        if output_path:
            try:
                # Invocación directa a la API para compilar y guardar el nuevo archivo
                final_file = PhoenixGCodeAPI.execute_recovery(
                    input_path=self._selected_file,
                    output_path=output_path,
                    measured_z=self._measured_z,
                    strategy_name=self._strategy,
                    override_hotend_temp=self._override_hotend,
                    override_bed_temp=self._override_bed,
                )
                self._status_message = f"✔ Archivo de recuperación guardado con éxito en:\n{final_file}"
                self.statusMessageChanged.emit(self._status_message)

            except Exception as e:
                self._status_message = f"Error al escribir archivo: {str(e)}"
                self.statusMessageChanged.emit(self._status_message)

    # --- Propiedades QML para Binding Visual ---

    @pyqtProperty(str, notify=planUpdated)
    def selectedFile(self):
        return self._selected_file

    @pyqtProperty(int, notify=planUpdated)
    def candidateLine(self):
        return self._candidate_line

    @pyqtProperty(float, notify=planUpdated)
    def candidateZ(self):
        return self._candidate_z

    @pyqtProperty(float, notify=planUpdated)
    def confidenceScore(self):
        return self._confidence_score

    @pyqtProperty(str, notify=statusMessageChanged)
    def statusMessage(self):
        return self._status_message