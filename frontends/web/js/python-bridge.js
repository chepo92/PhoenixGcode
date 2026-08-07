/**
 * PythonBridge: Invocación oficial de PhoenixGCodeAPI mapeada al Core real.
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
     * Mapeado a PhoenixGCodeAPI.plan_recovery
     */
    async planRecovery(filename, arrayBuffer, measuredZ, strategyName = "HOME_XY", candidateIndex = 0) {
        const virtualPath = `/tmp/${filename}`;
        this.pyodide.FS.writeFile(virtualPath, new Uint8Array(arrayBuffer));

        const code = `
            import json
            res = PhoenixGCodeAPI.plan_recovery(
                file_path="${virtualPath}",
                measured_z=${measuredZ},
                candidate_index=${candidateIndex},
                strategy_name="${strategyName}"
            )
            json.dumps(res)
        `;

        const jsonResultStr = await this.pyodide.runPythonAsync(code);
        try { this.pyodide.FS.unlink(virtualPath); } catch (e) {}

        return JSON.parse(jsonResultStr);
    }

    /**
     * Mapeado a PhoenixGCodeAPI.execute_recovery
     */
    async executeRecovery(filename, arrayBuffer, measuredZ, candidateIndex, strategyName, overrideHotendTemp = null, overrideBedTemp = null) {
        const virtualPath = `/tmp/${filename}`;
        const outputPath = `/tmp/recovery_${filename}`;
        this.pyodide.FS.writeFile(virtualPath, new Uint8Array(arrayBuffer));

        const code = `
            import json
            from phoenixgcode.api import PhoenixGCodeAPI
            
            out_file = PhoenixGCodeAPI.execute_recovery(
                input_path="${virtualPath}",
                output_path="${outputPath}",
                measured_z=${measuredZ},
                candidate_index=${candidateIndex},
                strategy_name="${strategyName}",
                override_hotend_temp=${overrideHotendTemp !== null ? overrideHotendTemp : 'None'},
                override_bed_temp=${overrideBedTemp !== null ? overrideBedTemp : 'None'}
            )
            
            with open(out_file, "r", encoding="utf-8", errors="ignore") as f:
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