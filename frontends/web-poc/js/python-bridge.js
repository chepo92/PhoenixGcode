/**
 * PythonBridge: Carga PhoenixGCode instalando el paquete Wheel (.whl) nativo via micropip.
 */
class PhoenixPythonBridge {
    constructor() {
        this.pyodide = null;
        this.metrics = {
            pyodideLoadTime: 0,
            phoenixLoadTime: 0,
        };
    }

    async init(onStatusUpdate) {
        const t0 = performance.now();

        // 1. Cargar Runtime de Pyodide
        onStatusUpdate("Cargando Python Runtime (Pyodide)...");
        this.pyodide = await loadPyodide();
        const t1 = performance.now();
        this.metrics.pyodideLoadTime = t1 - t0;

        // 2. Cargar micropip e instalar chardet
        onStatusUpdate("Cargando micropip e instalando chardet...");
        await this.pyodide.loadPackage("micropip");
        const micropip = this.pyodide.pyimport("micropip");
        await micropip.install("chardet");

        // 3. Localizar e instalar el Wheel (.whl) de PhoenixGCode
        onStatusUpdate("Instalando Wheel de PhoenixGCode...");
        const whlUrl = await this._findWheelUrl();
        await micropip.install(whlUrl);

        // 4. Verificar importación de la API
        this.pyodide.runPython(`
            from phoenixgcode.api import PhoenixGCodeAPI
        `);
        const t2 = performance.now();
        this.metrics.phoenixLoadTime = t2 - t1;

        onStatusUpdate("Ready.");
    }

    /**
     * Busca el archivo .whl generado en la carpeta dist/ probando rutas relativas.
     */
    async _findWheelUrl() {
        const candidateURLs = [
            `../../dist/phoenixgcode-0.1.0-py3-none-any.whl`,
            `/dist/phoenixgcode-0.1.0-py3-none-any.whl`,
            `./dist/phoenixgcode-0.1.0-py3-none-any.whl`,
            `../dist/phoenixgcode-0.1.0-py3-none-any.whl`
        ];

        for (const url of candidateURLs) {
            try {
                const response = await fetch(url, { method: 'HEAD' });
                if (response.ok) return url;
            } catch (e) {}
        }
        throw new Error("No se encontró el archivo .whl en 'dist/'. Asegúrate de ejecutar 'python -m build --wheel'.");
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

    getMemoryUsageMB() {
        if (this.pyodide && this.pyodide._module && this.pyodide._module.HEAP8) {
            return (this.pyodide._module.HEAP8.buffer.byteLength / (1024 * 1024)).toFixed(2);
        }
        return "N/A";
    }
}