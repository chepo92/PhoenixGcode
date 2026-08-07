$(function() {
    function PhoenixGCodeViewModel(parameters) {
        var self = this;

        self.availableFiles = ko.observableArray([]);
        self.selectedFile = ko.observable();
        self.measuredZ = ko.observable(0.0);
        self.selectedStrategy = ko.observable("HOME_XY");
        self.planResult = ko.observable(null);

        // Cargar lista de archivos G-code desde OctoPrint
        self.loadFiles = function() {
            $.ajax({
                url: "/api/plugin/phoenixgcode",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({ command: "list_gcode_files" }),
                success: function(response) {
                    if (response.status === "success") {
                        self.availableFiles(response.files);
                    }
                }
            });
        };

        // Solicitar creación de RecoveryPlan
        self.planRecovery = function() {
            $.ajax({
                url: "/api/plugin/phoenixgcode",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "plan_recovery",
                    target_file: self.selectedFile(),
                    measured_z: parseFloat(self.measuredZ()),
                    strategy: self.selectedStrategy()
                }),
                success: function(response) {
                    if (response.status === "success") {
                        self.planResult(response.plan);
                    }
                }
            });
        };

        // Generar y subir el archivo a OctoPrint
        self.executeRecovery = function() {
            $.ajax({
                url: "/api/plugin/phoenixgcode",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "execute_recovery",
                    target_file: self.selectedFile(),
                    measured_z: parseFloat(self.measuredZ()),
                    strategy: self.selectedStrategy()
                }),
                success: function(response) {
                    if (response.status === "success") {
                        new PNotify({
                            title: 'PhoenixGCode Success',
                            text: 'Archivo generado y subido a OctoPrint: ' + response.recovery_file_name,
                            type: 'success'
                        });
                        self.loadFiles();
                    }
                }
            });
        };

        self.onStartup = function() {
            self.loadFiles();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PhoenixGCodeViewModel,
        dependencies: ["settingsViewModel", "loginStateViewModel"],
        elements: ["#tab_plugin_phoenixgcode"]
    });
});