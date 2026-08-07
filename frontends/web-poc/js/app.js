document.addEventListener("DOMContentLoaded", () => {
    const bridge = new PhoenixPythonBridge();

    const statusIndicator = document.getElementById("status-indicator");
    const statusSpinner = document.getElementById("status-spinner");
    const statusText = document.getElementById("status-text");
    const runtimeMetrics = document.getElementById("runtime-metrics");
    const uploadCard = document.getElementById("upload-card");
    const fileInput = document.getElementById("gcode-file-input");
    const resultsCard = document.getElementById("results-card");

    bridge.init((statusMsg) => {
        statusText.innerText = statusMsg;
    }).then(() => {
        statusSpinner.classList.add("hidden");
        statusIndicator.classList.remove("loading");
        statusIndicator.classList.add("ready");
        
        document.getElementById("time-pyodide").innerText = `${bridge.metrics.pyodideLoadTime.toFixed(2)} ms`;
        document.getElementById("time-phoenix").innerText = `${bridge.metrics.phoenixLoadTime.toFixed(2)} ms`;
        document.getElementById("memory-wasm").innerText = `${bridge.getMemoryUsageMB()} MB`;
        
        runtimeMetrics.classList.remove("hidden");
        uploadCard.classList.remove("disabled");
        fileInput.disabled = false;
    }).catch((err) => {
        statusSpinner.classList.add("hidden");
        statusText.innerText = `Error fatal iniciando Pyodide: ${err.message}`;
        statusText.style.color = "red";
    });

    fileInput.addEventListener("change", async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        resultsCard.classList.add("hidden");

        const tStart = performance.now();
        // Carga binaria en ArrayBuffer (ultra rápido y seguro para cualquier encoding)
        const arrayBuffer = await file.arrayBuffer();
        const tRead = performance.now();
        const readTimeMs = tRead - tStart;

        try {
            const analysis = await bridge.analyzeGCodeBinary(file.name, arrayBuffer);
            const tEnd = performance.now();
            const totalTimeMs = tEnd - tStart;

            document.getElementById("res-filename").innerText = file.name;
            document.getElementById("res-lines").innerText = analysis.total_lines.toLocaleString();
            document.getElementById("res-layers").innerText = analysis.total_layers;
            document.getElementById("res-zmax").innerText = `${analysis.max_z_height.toFixed(3)} mm`;
            document.getElementById("res-comments").innerText = analysis.comment_count;
            document.getElementById("res-encoding").innerText = "Detección Automática (GCodeReader)";

            document.getElementById("time-read").innerText = `${readTimeMs.toFixed(2)} ms`;
            document.getElementById("time-analysis").innerText = `${analysis.analysis_time_ms.toFixed(2)} ms`;
            document.getElementById("time-total").innerText = `${totalTimeMs.toFixed(2)} ms`;

            resultsCard.classList.remove("hidden");
        } catch (err) {
            alert(`Error al analizar el archivo con PhoenixGCodeAPI: ${err.message}`);
        }
    });
});