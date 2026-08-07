/**
 * Log de consola integrado para el Workspace.
 */
class WorkspaceConsole {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.logs = [];
    }

    log(msg, type = "info") {
        const timestamp = new Date().toLocaleTimeString();
        const line = `[${timestamp}] [${type.toUpperCase()}] ${msg}`;
        this.logs.push(line);

        const div = document.createElement("div");
        div.className = `console-entry console-${type}`;
        div.textContent = line;
        
        if (this.container) {
            this.container.appendChild(div);
            this.container.scrollTop = this.container.scrollHeight;
        }
    }

    warn(msg) { this.log(msg, "warn"); }
    error(msg) { this.log(msg, "error"); }

    copyToClipboard() {
        const fullText = this.logs.join("\n");
        navigator.clipboard.writeText(fullText).then(() => {
            alert("Consola copiada al portapapeles.");
        });
    }
}

window.appConsole = new WorkspaceConsole("workspace-console");