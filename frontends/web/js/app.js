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
    let currentPlanData = null;
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
        currentPlanData = null;
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

            // Renderizar Información del Core dinámicamente según la respuesta real de la API
            const firmwareVal = analysis.slicer || analysis.firmware || analysis.source_file ? "Marlin / Slicer Detectado" : "Desconocido";
            document.getElementById("info-firmware").innerText = firmwareVal;

            document.getElementById("info-lines").innerText = (analysis.total_lines || 0).toLocaleString();
            document.getElementById("info-layers").innerText = analysis.total_layers !== undefined ? analysis.total_layers : "-";

            if (analysis.max_z_height !== undefined) {
                document.getElementById("info-zrange").innerText = `0.00 - ${Number(analysis.max_z_height).toFixed(2)} mm`;
            } else {
                document.getElementById("info-zrange").innerText = "-";
            }

            // Extrusión
            const extrusionMode = analysis.extrusion_mode || "ABSOLUTE (M82)";
            document.getElementById("info-extrusion").innerText = extrusionMode;

            // Temperaturas extraídas del análisis si están disponibles
            const hotendTemp = analysis.hotend_temp || analysis.target_hotend_temp || 200;
            const bedTemp = analysis.bed_temp || analysis.target_bed_temp || 60;
            document.getElementById("info-temps").innerText = `${hotendTemp}°C / ${bedTemp}°C`;

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

    // Calcular plan de recuperación llamando a plan_recovery
    btnCalcPlan.addEventListener("click", async () => {
        const measuredZ = parseFloat(recZInput.value);
        if (isNaN(measuredZ) || measuredZ <= 0) {
            window.appConsole.warn("Ingresa una altura Z válida mayor a 0 mm.");
            return;
        }

        const strategyName = recHomeMode.value || "HOME_XY";
        window.appConsole.log(`Consultando PhoenixGCodeAPI.plan_recovery con Z=${measuredZ}mm, Estrategia=${strategyName}...`);
        recLayerSelect.disabled = true;
        recLayerSelect.innerHTML = "<option>Buscando candidatos...</option>";

        try {
            currentPlanData = await bridge.planRecovery(currentFileName, currentFileBuffer, measuredZ, strategyName);
            const candidates = currentPlanData.candidates || [];

            recLayerSelect.innerHTML = "";
            if (candidates.length === 0) {
                recLayerSelect.innerHTML = "<option value=''>No se encontraron candidatos</option>";
                window.appConsole.warn("No se encontraron puntos de recuperación para esa altura Z.");
            } else {
                candidates.forEach((cand) => {
                    const opt = document.createElement("option");
                    opt.value = cand.index;
                    opt.innerText = `Candidato #${cand.index} | Capa: ${cand.layer_index} | Z Target: ${cand.target_z}mm | Línea: ${cand.line_number}`;
                    recLayerSelect.appendChild(opt);
                });
                recLayerSelect.disabled = false;

                // Poblar estado reconstruido (extrusor)
                if (currentPlanData.reconstructed_state && currentPlanData.reconstructed_state.extruder_e !== undefined) {
                    recExtrusionVal.value = currentPlanData.reconstructed_state.extruder_e.toFixed(3);
                }

                btnGenerateRecovery.disabled = false;
                window.appConsole.log(`Core devolvió ${candidates.length} punto(s) candidato(s).`);
            }
        } catch (err) {
            window.appConsole.error(`Error en plan_recovery: ${err.message}`);
        }
    });

    // Generar archivo final G-Code llamando a execute_recovery
    btnGenerateRecovery.addEventListener("click", async () => {
        const measuredZ = parseFloat(recZInput.value);
        const candidateIdx = parseInt(recLayerSelect.value) || 0;
        const strategyName = recHomeMode.value || "HOME_XY";

        window.appConsole.log(`Iniciando PhoenixGCodeAPI.execute_recovery (Candidato #${candidateIdx}, Estrategia=${strategyName})...`);

        try {
            generatedGCodeContent = await bridge.executeRecovery(
                currentFileName,
                currentFileBuffer,
                measuredZ,
                candidateIdx,
                strategyName
            );

            // Vista previa de las primeras 35 líneas
            const previewLines = generatedGCodeContent.split("\n").slice(0, 35).join("\n");
            recoveryPreview.textContent = previewLines + "\n\n... [Contenido recortado en la vista previa] ...";

            previewCard.classList.remove("hidden");
            previewCard.scrollIntoView({ behavior: 'smooth' });

            window.appConsole.log("Archivo de recuperación compilado exitosamente por el Core.");
        } catch (err) {
            window.appConsole.error(`Error en execute_recovery: ${err.message}`);
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