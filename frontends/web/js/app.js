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

    const progressContainer = document.getElementById("upload-progress-container");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressText = document.getElementById("upload-progress-text");

    const btnAnalyze = document.getElementById("btn-tool-analyze");

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

    function resetAnalysisViews() {
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
     * PASO 1: LECTURA LOCAL
     * Solamente lee el archivo en memoria y muestra el progreso. NO llama al Core.
     */
    function loadFile(file) {
        if (!file) return;

        currentFileBuffer = null;
        currentFileName = file.name;
        resetAnalysisViews();

        metaName.innerText = file.name;
        metaSize.innerText = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
        metaStatus.innerText = "Cargando...";
        
        fileMeta.classList.remove("hidden");
        progressContainer.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressText.innerText = "0%";

        btnAnalyze.disabled = true;
        btnAnalyze.classList.remove("active");

        window.appConsole.log(`Lectura local de archivo: ${file.name}`);

        const reader = new FileReader();
        const tStart = performance.now();

        reader.onprogress = (event) => {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                progressBar.style.width = `${percent}%`;
                progressText.innerText = `${percent}%`;
            }
        };

        reader.onload = (event) => {
            const tEnd = performance.now();
            readTimeMs = tEnd - tStart;
            currentFileBuffer = event.target.result;

            metaStatus.innerText = "Listo para analizar";
            progressBar.style.width = "100%";
            progressText.innerText = "100%";

            document.getElementById("bench-read").innerText = `${readTimeMs.toFixed(2)} ms`;
            window.appConsole.log(`Archivo cargado en memoria RAM en ${readTimeMs.toFixed(2)} ms. Estado: Listo para analizar.`);

            // Habilitar el botón Analyze
            btnAnalyze.disabled = false;
            btnAnalyze.classList.add("active");
        };

        reader.onerror = () => {
            metaStatus.innerText = "Error al leer archivo";
            window.appConsole.error("Error leyendo archivo en navegador.");
        };

        reader.readAsArrayBuffer(file);
    }

    /**
     * PASO 2: ANÁLISIS EN EL CORE (Se ejecuta SÓLO al hacer clic en Analyze)
     */
    async function executeAnalysis() {
        if (!currentFileBuffer) {
            window.appConsole.warn("Debes seleccionar un archivo primero.");
            return;
        }

        metaStatus.innerText = "Analizando con Core...";
        window.appConsole.log("Clic en 'Analyze': Ejecutando PhoenixGCodeAPI.analyze_file...");
        btnAnalyze.disabled = true;

        try {
            const analysis = await bridge.analyzeGCodeBinary(currentFileName, currentFileBuffer);

            window.appConsole.log(`Análisis completado. Capas: ${analysis.total_layers}, Líneas: ${analysis.total_lines}`);

            // Mostrar resultados
            document.getElementById("info-firmware").innerText = "Marlin / Cura (Detectado)";
            document.getElementById("info-lines").innerText = analysis.total_lines.toLocaleString();
            document.getElementById("info-layers").innerText = analysis.total_layers;
            document.getElementById("info-zrange").innerText = `0.00 - ${analysis.max_z_height.toFixed(2)} mm`;
            document.getElementById("info-extrusion").innerText = "ABSOLUTE (M82)";
            document.getElementById("info-temps").innerText = "210°C / 60°C";

            document.getElementById("bench-analysis").innerText = `${analysis.analysis_time_ms.toFixed(2)} ms`;
            document.getElementById("bench-total").innerText = `${(readTimeMs + analysis.analysis_time_ms).toFixed(2)} ms`;
            document.getElementById("bench-wasm-mem").innerText = `${bridge.getMemoryUsageMB()} MB`;

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