import QtQuick 2.7
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.3
import UM 1.5 as UM

UM.Dialog {
    id: recoveryDialog
    title: "PhoenixGCode - Print Recovery Tool"
    width: 550
    height: 480
    minimumWidth: 500
    minimumHeight: 450

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        // Banner del Plugin
        Label {
            text: "PhoenixGCode Recovery Plan"
            font.bold: true
            font.pointSize: 14
        }

        Label {
            text: "Understand G-code before changing it."
            font.italic: true
            color: "#666666"
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#cccccc" }

        // Sección 1: Selección de Archivo
        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: filePathField
                text: manager.selectedFile
                placeholderText: "Seleccione un archivo .gcode..."
                readOnly: true
                Layout.fillWidth: true
            }
            Button {
                text: "Examinar..."
                onClicked: manager.browseFile()
            }
        }

        // Sección 2: Configuración del usuario (RecoverySettings)
        GridLayout {
            columns: 2
            rowSpacing: 8
            columnSpacing: 12
            Layout.fillWidth: true

            Label { text: "Altura Z Medida (mm):"; font.bold: true }
            TextField {
                id: measuredZInput
                text: "0.0"
                placeholderText: "Ej. 12.4"
                validator: DoubleValidator { bottom: 0.0; top: 1000.0; decimals: 3 }
            }

            Label { text: "Estrategia de Recovery:" }
            ComboBox {
                id: strategyCombo
                model: ["HOME_XY", "MANUAL_POSITION", "HOME_XYZ", "CUSTOM_SCRIPT"]
                currentIndex: 0
            }

            Label { text: "Override Hotend Temp (ºC):" }
            TextField {
                id: hotendTempInput
                placeholderText: "0 = Autodetectar"
                text: "0"
            }

            Label { text: "Override Cama Temp (ºC):" }
            TextField {
                id: bedTempInput
                placeholderText: "0 = Autodetectar"
                text: "0"
            }
        }

        Button {
            text: "Calcular Recovery Plan"
            highlighted: true
            Layout.alignment: Qt.AlignRight
            onClicked: {
                var zVal = parseFloat(measuredZInput.text) || 0.0;
                var hotendVal = parseFloat(hotendTempInput.text) || 0.0;
                var bedVal = parseFloat(bedTempInput.text) || 0.0;
                manager.calculateRecoveryPlan(zVal, strategyCombo.currentText, hotendVal, bedVal);
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#cccccc" }

        // Sección 3: Resultados del Plan de Recuperación
        GroupBox {
            title: "Resumen del Recovery Plan"
            Layout.fillWidth: true

            ColumnLayout {
                spacing: 4
                Label { text: "Línea de Reanudación: " + manager.candidateLine }
                Label { text: "Altura Z detectada: " + manager.candidateZ.toFixed(3) + " mm" }
                Label { text: "Confianza del Plan: " + manager.confidenceScore.toFixed(1) + "%" }
            }
        }

        Label {
            id: statusLabel
            text: manager.statusMessage
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            color: "#0066cc"
        }

        // Acciones Finales
        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: "Cerrar"
                onClicked: recoveryDialog.close()
            }
            Button {
                text: "Generar Recovery.gcode"
                enabled: manager.candidateLine > 0
                onClicked: manager.generateRecoveryFile()
            }
        }
    }
}