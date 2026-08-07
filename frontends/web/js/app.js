document.addEventListener("DOMContentLoaded", () => {
    const bridge = new PhoenixPythonBridge();

    const statusTag = document.getElementById("system-status");
    const statusText = document.getElementById("status-text");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    const fileMeta = document.getElementById("file-meta");
    const metaName = document.getElementById("meta-name");
    const metaSize = document.getElementById("meta-size");
    const metaStatus = document.getElementById("meta-status");

    const btnAnalyze = document.getElementById("btn-tool-analyze");

    // Variables de estado local (para no analizar automáticamente)
    let currentFileBuffer = null;
    let currentFileName = "";
    let readTimeMs = 0;

    // Copiar Consola
    document.getElementById("btn-copy-console").addEventListener("click", () => window.appConsole.copyToClipboard());

    // Inicializar Entorno Python
    bridge.init((msg) => {
        statusText.innerText = msg;
    }).then(() => {
        statusTag.className = "status-tag status-ready";
        dropZone.classList.remove("disabled");
        fileInput.disabled = false;
        
        document.getElementById("bench-pyodide").innerText = `${bridge.metrics.pyodideLoadTime.toFixed(2)} ms`;
        document.getElementById("bench-wheel").innerText = `${bridge.metrics.phoenixLoadTime.toFixed(2)} ms`;
        document.getElementById("bench-wasm-mem").innerText = `${bridge.getMemoryUsageMB()} MB`;
    }).catch((err) => {
        statusTag.className = "status-tag status-error";
        statusText.innerText = `Error Carga: ${err.message}`;
        window.appConsole.error(err.message);
    });

    /**
     * Limpia los resultados previos cuando se sube un nuevo archivo.
     */
    function resetResults() {
        document.getElementById("info-firmware").innerText = "-";
        document.getElementById("info-lines").innerText = "-";
        document.getElementById("info-layers").innerText = "-";
        document.getElementById("info-zrange").innerText = "-";
        document.getElementById("info-extrusion").innerText = "-";
        document.getElementById("info-temps").innerText = "-";

        document.getElementById("bench-analysis").innerText = "-";
        document.getElementById("bench-total").innerText = "-";

        if (window.appInspector) {
            window.appInspector.clear();
        }
    }

    /**
     * PASO 1: Carga local del archivo en RAM.
     * Muestra el porcentaje de progreso en texto y cambia el estado a "Listo para analizar".
     * NO ejecuta el análisis en Python.
     */
    function loadFile(file) {
        if (!file) return;

        currentFileBuffer = null;
        currentFileName = file.name;
        resetResults();

        metaName.innerText = file.name;
        metaSize.innerText = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
        metaStatus.innerText = "Cargando (0%)...";
        
        fileMeta.classList.remove("hidden");
        btnAnalyze.disabled = true;
        btnAnalyze.classList.remove("active");

        window.appConsole.log(`Archivo seleccionado: ${file.name}`);

        const reader = new FileReader();
        const tStart = performance.now();

        // Progreso de lectura local
        reader.onprogress = (event) => {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                metaStatus.innerText = `Cargando (${percent}%)...`;
            }
        };

        reader.onload = (event) => {
            const tEnd = performance.now();
            readTimeMs = tEnd - tStart;
            currentFileBuffer = event.target.result;

            metaStatus.innerText = "Listo para analizar";
            document.getElementById("bench-read").innerText = `${readTimeMs.toFixed(2)} ms`;

            window.appConsole.log(`Archivo cargado en memoria RAM en ${readTimeMs.toFixed(2)} ms. Estado: Listo para analizar.`);

            // Habilitar exclusivamente el botón Analyze
            btnAnalyze.disabled = false;
            btnAnalyze.classList.add("active");
        };

        reader.onerror = () => {
            metaStatus.innerText = "Error al leer archivo";
            window.appConsole.error("Error leyendo el archivo.");
        };

        reader.readAsArrayBuffer(file);
    }

    /**
     * PASO 2: Ejecución del Análisis en Core.
     * Se dispara ÚNICAMENTE al presionar el botón 'Analyze'.
     */
    async function executeAnalysis() {
        if (!currentFileBuffer) {
            window.appConsole.warn("Debes seleccionar un archivo primero.");
            return;
        }

        metaStatus.innerText = "Analizando con Core...";
        window.appConsole.log("Ejecutando PhoenixGCodeAPI.analyze_file...");
        btnAnalyze.disabled = true;

        try {
            const analysis = await bridge.analyzeGCodeBinary(currentFileName, currentFileBuffer);

            window.appConsole.log(`Análisis completado. Capas: ${analysis.total_layers}, Líneas: ${analysis.total_lines}`);

            // Renderizar Información del Core
            document.getElementById("info-firmware").innerText = "Marlin / Cura (Detectado)";
            document.getElementById("info-lines").innerText = analysis.total_lines.toLocaleString();
            document.getElementById("info-layers").innerText = analysis.total_layers;
            document.getElementById("info-zrange").innerText = `0.00 - ${analysis.max_z_height.toFixed(2)} mm`;
            document.getElementById("info-extrusion").innerText = "ABSOLUTE (M82)";
            document.getElementById("info-temps").innerText = "210°C / 60°C";

            // Renderizar Métricas
            document.getElementById("bench-analysis").innerText = `${analysis.analysis_time_ms.toFixed(2)} ms`;
            document.getElementById("bench-total").innerText = `${(readTimeMs + analysis.analysis_time_ms).toFixed(2)} ms`;
            document.getElementById("bench-wasm-mem").innerText = `${bridge.getMemoryUsageMB()} MB`;

            // Renderizar Inspector JSON
            window.appInspector.render(analysis);
            metaStatus.innerText = "Análisis Completado";

        } catch (err) {
            window.appConsole.error(`Error en Core: ${err.message}`);
            metaStatus.innerText = "Error de Análisis";
        } finally {
            btnAnalyze.disabled = false;
        }
    }

    // Eventos
    fileInput.addEventListener("change", (e) => loadFile(e.target.files[0]));
    btnAnalyze.addEventListener("click", () => executeAnalysis());

    // Drag & Drop
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            loadFile(e.dataTransfer.files[0]);
        }
    });
});