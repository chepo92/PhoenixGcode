/**
 * Inspector JSON para visualizar objetos del Core sin alterarlos.
 */
class WorkspaceInspector {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    render(dataObj) {
        if (!this.container) return;
        this.container.textContent = JSON.stringify(dataObj, null, 2);
    }

    clear() {
        if (this.container) this.container.textContent = "Esperando análisis...";
    }
}

window.appInspector = new WorkspaceInspector("json-inspector");