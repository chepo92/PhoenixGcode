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
    const btnToolRecover = document.getElementById("btn-tool-recover");

    const recoveryCard = document.getElementById("recovery-card");
    const recZInput = document.getElementById("rec-z-height");
    const btnCalcPlan = document.getElementById("btn-calc-plan");
    const recLayerSelect = document.getElementById("rec-layer-select");
    const recHomeMode = document.getElementById("rec-home-mode");
    const recExtrusionVal = document.getElementById("rec-extrusion-val");
    const btnGenerateRecovery = document.getElementById("btn-generate-recovery");

    const previewCard = document.getElementById("preview-card");
    const recoveryPreview = document.getElementById("recovery-preview");
    const btnDownloadRecovery = document.getElementById("btn-download-recovery");

    let currentFileBuffer = null;
    let currentFileName = "";
    let readTimeMs = 0;
    let currentCandidates = [];
    let generatedGCodeContent = null;

    document.getElementById("btn-copy-console").addEventListener("click", () => window.appConsole.copyToClipboard());

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
        statusText.innerText = `Error: ${err.message}`;
        window.appConsole.error(err.message);
    });

    function resetWorkspace() {
        recoveryCard.classList.add("hidden");
        previewCard.classList.add("hidden");
        btnToolRecover.disabled = true;
        btnToolRecover.classList.remove("active");
        currentCandidates = [];
        generatedGCodeContent = null;
    }

    function loadFile(file) {
        if (!file) return;

        currentFileBuffer = null;
        currentFileName = file.name;
        resetWorkspace();

        metaName.innerText = file.name;
        metaSize.innerText = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
        metaStatus.innerText = "Cargando (0%)...";

        fileMeta.classList.remove("hidden");
        btnAnalyze.disabled = true;

        const reader = new FileReader();
        const tStart = performance.now();

        reader.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                metaStatus.innerText = `Cargando (${percent}%)...`;
            }
        };

        reader.onload = (e) => {
            const tEnd = performance.now();
            readTimeMs = tEnd - tStart;
            currentFileBuffer = e.target.result;

            metaStatus.innerText = "Listo para analizar";
            document.getElementById("bench-read").innerText = `${readTimeMs.toFixed(2)} ms`;
            window.appConsole.log(`Archivo cargado en RAM (${readTimeMs.toFixed(2)} ms).`);

            btnAnalyze.disabled = false;
            btnAnalyze.classList.add("active");
        };

        reader.readAsArrayBuffer(file);
    }

    async function executeAnalysis() {
        if (!currentFileBuffer) return;

        metaStatus.innerText = "Analizando con Core...";
        window.appConsole.log("Ejecutando PhoenixGCodeAPI.analyze_file...");

        try {
            const analysis = await bridge.analyzeGCodeBinary(currentFileName, currentFileBuffer);

            document.getElementById("info-firmware").innerText = "Detectado por Core";
            document.getElementById("info-lines").innerText = analysis.total_lines.toLocaleString();
            document.getElementById("info-layers").innerText = analysis.total_layers;
            document.getElementById("info-zrange").innerText = `0.00 - ${analysis.max_z_height.toFixed(2)} mm`;
            document.getElementById("info-extrusion").innerText = "ABSOLUTE";
            document.getElementById("info-temps").innerText = "Ok";

            document.getElementById("bench-analysis").innerText = `${analysis.analysis_time_ms.toFixed(2)} ms`;
            document.getElementById("bench-total").innerText = `${(readTimeMs + analysis.analysis_time_ms).toFixed(2)} ms`;

            window.appInspector.render(analysis);
            metaStatus.innerText = "Análisis Completado";

            // Activar botón de Recovery
            btnToolRecover.disabled = false;
            btnToolRecover.classList.add("active");
            window.appConsole.log("Análisis exitoso. Herramienta Recovery habilitada.");

        } catch (err) {
            window.appConsole.error(`Error en análisis: ${err.message}`);
            metaStatus.innerText = "Error de Análisis";
        }
    }

    // Activar panel de Recovery
    btnToolRecover.addEventListener("click", () => {
        recoveryCard.classList.remove("hidden");
        recoveryCard.scrollIntoView({ behavior: 'smooth' });
        window.appConsole.log("Panel Recovery activado.");
    });

    // Calcular capas candidatas
    btnCalcPlan.addEventListener("click", async () => {
        const targetZ = parseFloat(recZInput.value);
        if (isNaN(targetZ) || targetZ <= 0) {
            window.appConsole.warn("Ingresa una altura Z válida mayor a 0 mm.");
            return;
        }

        window.appConsole.log(`Consultando Core para capas candidatas en Z=${targetZ} mm...`);
        recLayerSelect.disabled = true;
        recLayerSelect.innerHTML = "<option>Buscando candidatos...</option>";

        try {
            const plan = await bridge.buildRecoveryPlan(currentFileName, currentFileBuffer, targetZ);
            currentCandidates = plan.candidates || [];

            recLayerSelect.innerHTML = "";
            if (currentCandidates.length === 0) {
                recLayerSelect.innerHTML = "<option value=''>No se encontraron capas candidatas</option>";
                window.appConsole.warn("El Core no devolvió candidatos para la altura Z especificada.");
            } else {
                currentCandidates.forEach((cand, idx) => {
                    const opt = document.createElement("option");
                    opt.value = idx;
                    opt.innerText = `Capa ${cand.layer_index} (Z=${cand.z_height} mm) - L:${cand.line_number}`;
                    recLayerSelect.appendChild(opt);
                });
                recLayerSelect.disabled = false;
                
                // Actualizar valor E por defecto
                if (currentCandidates[0].initial_extrusion !== undefined) {
                    recExtrusionVal.value = currentCandidates[0].initial_extrusion;
                }

                btnGenerateRecovery.disabled = false;
                window.appConsole.log(`Core devolvió ${currentCandidates.length} capas candidatas.`);
            }
        } catch (err) {
            window.appConsole.error(`Error calculando Recovery Plan: ${err.message}`);
        }
    });

    // Al cambiar la capa elegida, actualizar el valor E
    recLayerSelect.addEventListener("change", (e) => {
        const idx = parseInt(e.target.value);
        if (!isNaN(idx) && currentCandidates[idx]) {
            recExtrusionVal.value = currentCandidates[idx].initial_extrusion || 0;
        }
    });

    // Generar archivo final G-Code
    btnGenerateRecovery.addEventListener("click", async () => {
        const candidateIdx = parseInt(recLayerSelect.value);
        const homeMode = recHomeMode.value;
        const overrideE = recExtrusionVal.value ? parseFloat(recExtrusionVal.value) : null;

        window.appConsole.log(`Iniciando generación de G-code con Capa Índice ${candidateIdx}, Home=${homeMode}...`);

        try {
            generatedGCodeContent = await bridge.generateRecoveryGCode(
                currentFileName,
                currentFileBuffer,
                candidateIdx,
                homeMode,
                overrideE
            );

            // Muestra de las primeras líneas en la vista previa
            const previewLines = generatedGCodeContent.split("\n").slice(0, 30).join("\n");
            recoveryPreview.textContent = previewLines + "\n\n... [Contenido truncado en la vista previa] ...";

            previewCard.classList.remove("hidden");
            previewCard.scrollIntoView({ behavior: 'smooth' });

            window.appConsole.log("Archivo de recuperación generado exitosamente en memoria.");
        } catch (err) {
            window.appConsole.error(`Error generando G-Code de recuperación: ${err.message}`);
        }
    });

    // Descargar archivo generado
    btnDownloadRecovery.addEventListener("click", () => {
        if (!generatedGCodeContent) return;

        const blob = new Blob([generatedGCodeContent], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `recovery_${currentFileName}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        window.appConsole.log(`Descargado archivo: recovery_${currentFileName}`);
    });

    fileInput.addEventListener("change", (e) => loadFile(e.target.files[0]));
    btnAnalyze.addEventListener("click", () => executeAnalysis());

    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) loadFile(e.dataTransfer.files[0]);
    });
});