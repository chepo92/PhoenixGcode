/**
 * PythonBridge: Invocación oficial de PhoenixGCodeAPI.
 */
class PhoenixPythonBridge {
    constructor() {
        this.pyodide = null;
        this.metrics = { pyodideLoadTime: 0, phoenixLoadTime: 0 };
    }

    async init(onStatusUpdate) {
        const t0 = performance.now();
        onStatusUpdate("Cargando Pyodide Runtime...");
        window.appConsole.log("Inicializando Pyodide WASM...");

        this.pyodide = await loadPyodide();
        const t1 = performance.now();
        this.metrics.pyodideLoadTime = t1 - t0;

        onStatusUpdate("Instalando dependencias (chardet)...");
        await this.pyodide.loadPackage("micropip");
        const micropip = this.pyodide.pyimport("micropip");
        await micropip.install("chardet");

        onStatusUpdate("Instalando Wheel de PhoenixGCode...");
        const whlUrl = await this._findWheelUrl();
        await micropip.install(whlUrl);

        this.pyodide.runPython(`from phoenixgcode.api import PhoenixGCodeAPI`);
        const t2 = performance.now();
        this.metrics.phoenixLoadTime = t2 - t1;

        onStatusUpdate("Ready.");
    }

    async _findWheelUrl() {
        const candidateURLs = [
            `../../dist/phoenixgcode-0.1.0-py3-none-any.whl`,
            `/dist/phoenixgcode-0.1.0-py3-none-any.whl`,
            `./dist/phoenixgcode-0.1.0-py3-none-any.whl`
        ];

        for (const url of candidateURLs) {
            try {
                const response = await fetch(url, { method: 'HEAD' });
                if (response.ok) return url;
            } catch (e) {}
        }
        throw new Error("No se encontró el Wheel en dist/. Ejecuta 'python -m build --wheel'.");
    }

    async analyzeGCodeBinary(filename, arrayBuffer) {
        const virtualPath = `/tmp/${filename}`;
        this.pyodide.FS.writeFile(virtualPath, new Uint8Array(arrayBuffer));

        const code = `
            import json
            res = PhoenixGCodeAPI.analyze_file("${virtualPath}")
            json.dumps(res)
        `;

        const t0 = performance.now();
        const jsonResultStr = await this.pyodide.runPythonAsync(code);
        const t1 = performance.now();

        try { this.pyodide.FS.unlink(virtualPath); } catch (e) {}

        const resultObj = JSON.parse(jsonResultStr);
        resultObj.analysis_time_ms = t1 - t0;
        return resultObj;
    }

    /**
     * Construye el Recovery Plan llamando a PhoenixGCodeAPI.build_recovery_plan
     */
    async buildRecoveryPlan(filename, arrayBuffer, targetZ) {
        const virtualPath = `/tmp/${filename}`;
        this.pyodide.FS.writeFile(virtualPath, new Uint8Array(arrayBuffer));

        const code = `
            import json
            plan = PhoenixGCodeAPI.build_recovery_plan("${virtualPath}", target_z=${targetZ})
            json.dumps(plan)
        `;

        const jsonResultStr = await this.pyodide.runPythonAsync(code);
        try { this.pyodide.FS.unlink(virtualPath); } catch (e) {}

        return JSON.parse(jsonResultStr);
    }

    /**
     * Genera el nuevo archivo G-code recuperado llamando a PhoenixGCodeAPI.generate_recovery_gcode
     */
    async generateRecoveryGCode(filename, arrayBuffer, selectedCandidateIndex, homeMode, overrideE) {
        const virtualPath = `/tmp/${filename}`;
        const outputPath = `/tmp/recovery_${filename}`;
        this.pyodide.FS.writeFile(virtualPath, new Uint8Array(arrayBuffer));

        const code = `
            import json
            from phoenixgcode.api import PhoenixGCodeAPI
            
            plan_dict = PhoenixGCodeAPI.build_recovery_plan("${virtualPath}", target_z=0.0)
            
            # Invocar generación mediante la API
            out_path = PhoenixGCodeAPI.generate_recovery_gcode(
                original_filepath="${virtualPath}",
                output_filepath="${outputPath}",
                candidate_index=${selectedCandidateIndex},
                home_mode="${homeMode}",
                override_extrusion=${overrideE !== null ? overrideE : 'None'}
            )
            
            with open("${outputPath}", "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            content
        `;

        const generatedGCode = await this.pyodide.runPythonAsync(code);

        try { 
            this.pyodide.FS.unlink(virtualPath);
            this.pyodide.FS.unlink(outputPath);
        } catch (e) {}

        return generatedGCode;
    }

    getMemoryUsageMB() {
        if (this.pyodide && this.pyodide._module && this.pyodide._module.HEAP8) {
            return (this.pyodide._module.HEAP8.buffer.byteLength / (1024 * 1024)).toFixed(2);
        }
        return "N/A";
    }
}