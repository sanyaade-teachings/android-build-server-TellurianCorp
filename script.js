const projectGrid = document.getElementById("project-grid");
const emptyState = document.getElementById("empty-state");
const buildTypeSelect = document.getElementById("build-type");
const refreshBtn = document.getElementById("refresh-btn");
const deviceInput = document.getElementById("device-address");
const deviceSaveBtn = document.getElementById("device-save-btn");

const projectElements = new Map();

function titleize(text) {
    return text.replace(/_/g, " ");
}

function statusClass(status) {
    if (status === "done") return "success";
    if (status === "error") return "error";
    if (status && status !== "not_started") return "running";
    return "";
}

function buildProjectCard(project) {
    const card = document.createElement("div");
    card.className = "card";

    const header = document.createElement("div");
    header.className = "card-header";

    const name = document.createElement("div");
    name.className = "project-name";
    name.innerHTML = `<i class="fas fa-folder"></i> ${project}`;

    const pill = document.createElement("span");
    pill.className = "status-pill";
    pill.innerHTML = `<i class="fas fa-circle"></i> IDLE`;

    header.appendChild(name);
    header.appendChild(pill);

    const statusText = document.createElement("div");
    statusText.className = "status-text";
    statusText.textContent = "Not started";

    const progressLabel = document.createElement("div");
    progressLabel.className = "progress-label";
    progressLabel.innerHTML = `<span><i class="fas fa-tasks"></i> Progress</span><span>0%</span>`;

    const progress = document.createElement("div");
    progress.className = "progress";

    const progressBar = document.createElement("div");
    progressBar.className = "progress-bar";
    progress.appendChild(progressBar);

    const actions = document.createElement("div");
    actions.className = "actions";

    const buildBtn = document.createElement("button");
    buildBtn.className = "btn";
    buildBtn.innerHTML = `<i class="fas fa-play"></i> Start build`;

    const deployBtn = document.createElement("button");
    deployBtn.className = "btn secondary";
    deployBtn.innerHTML = `<i class="fas fa-rocket"></i> Deploy APK`;

    const artifact = document.createElement("div");
    artifact.className = "artifact";
    artifact.innerHTML = `<i class="fas fa-download"></i> Latest APK: <span class="muted">none</span>`;

    const viewLogsBtn = document.createElement("button");
    viewLogsBtn.className = "btn secondary view-logs-btn";
    viewLogsBtn.innerHTML = `<i class="fas fa-file-alt"></i> View Logs`;
    viewLogsBtn.style.display = "none";
    viewLogsBtn.addEventListener("click", () => showLogs(project));

    actions.appendChild(buildBtn);
    actions.appendChild(deployBtn);

    card.appendChild(header);
    card.appendChild(statusText);
    card.appendChild(progressLabel);
    card.appendChild(progress);
    card.appendChild(actions);
    card.appendChild(artifact);
    card.appendChild(viewLogsBtn);

    buildBtn.addEventListener("click", () => startBuild(project, buildBtn));
    deployBtn.addEventListener("click", () => deployProject(project, deployBtn));

    projectElements.set(project, {
        pill,
        statusText,
        progressLabel,
        progressBar,
        buildBtn,
        deployBtn,
        artifact,
        viewLogsBtn,
    });

    return card;
}

function updateProjectStatus(project, data) {
    const refs = projectElements.get(project);
    if (!refs) return;

    const status = data.status || "not_started";
    refs.statusText.textContent = titleize(status);
    
    // Update status pill with icon
    let statusIcon = "fa-circle";
    if (status === "done") statusIcon = "fa-check-circle";
    else if (status === "error") statusIcon = "fa-exclamation-circle";
    else if (status === "building" || status === "preparing" || status === "finding_apk") statusIcon = "fa-spinner fa-spin";
    else if (status === "deployed") statusIcon = "fa-check-circle";
    else if (status === "installing_apk" || status === "connecting_device") statusIcon = "fa-sync fa-spin";
    
    const statusText = status === "not_started" ? "IDLE" : status.toUpperCase();
    refs.pill.innerHTML = `<i class="fas ${statusIcon}"></i> ${statusText}`;
    refs.pill.className = `status-pill ${statusClass(status)}`.trim();

    const progress = Number.isFinite(data.progress) ? data.progress : 0;
    refs.progressBar.style.width = `${progress}%`;
    refs.progressLabel.innerHTML = `<span><i class="fas fa-tasks"></i> Progress</span><span>${progress}%</span>`;

    const isRunning = status !== "done" && status !== "error" && status !== "not_started" && status !== "deployed";
    refs.buildBtn.disabled = isRunning;
    refs.deployBtn.disabled = isRunning;

    // Show view logs button when there's an error
    if (status === "error") {
        refs.viewLogsBtn.style.display = "block";
    } else {
        refs.viewLogsBtn.style.display = "none";
    }

    if (data.artifact) {
        refs.artifact.innerHTML = `<i class="fas fa-download"></i> Latest APK: <a href="${data.artifact}" target="_blank" rel="noopener"><i class="fas fa-download"></i> Download</a>`;
    }

    if (data.message) {
        refs.statusText.textContent = `${titleize(status)} - ${data.message}`;
    }
}

function fetchProjects() {
    return fetch("/api/projects")
        .then((response) => response.json())
        .then((data) => {
            const projects = data.projects || [];
            projectGrid.innerHTML = "";
            projectElements.clear();

            if (!projects.length) {
                emptyState.hidden = false;
                return;
            }

            emptyState.hidden = true;
            projects.forEach((project) => {
                const card = buildProjectCard(project);
                projectGrid.appendChild(card);
            });

            updateAllStatuses();
        })
        .catch((error) => {
            console.error("Error loading projects:", error);
            emptyState.hidden = false;
        });
}

function updateStatusForProject(project) {
    return fetch(`/api/status?project=${encodeURIComponent(project)}`)
        .then((response) => response.json())
        .then((data) => updateProjectStatus(project, data))
        .catch((error) => console.error("Error fetching status:", error));
}

function updateAllStatuses() {
    const projects = Array.from(projectElements.keys());
    return Promise.all(projects.map(updateStatusForProject));
}

function startBuild(project, button) {
    button.disabled = true;
    fetch("/api/start-build", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            project,
            build_type: buildTypeSelect.value,
        }),
    })
        .then((response) => response.json())
        .then(() => updateStatusForProject(project))
        .catch((error) => {
            console.error("Error starting build:", error);
            button.disabled = false;
        });
}

function deployProject(project, button) {
    button.disabled = true;
    fetch("/api/deploy", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            project,
            build_type: buildTypeSelect.value,
        }),
    })
        .then((response) => response.json())
        .then(() => updateStatusForProject(project))
        .catch((error) => {
            console.error("Error deploying build:", error);
            button.disabled = false;
        });
}

function loadDevice() {
    fetch("/api/device")
        .then((response) => response.json())
        .then((data) => {
            if (data.address) {
                deviceInput.value = data.address;
            }
        })
        .catch((error) => console.error("Error loading device:", error));
}

function saveDevice() {
    const address = deviceInput.value.trim();
    fetch("/api/device", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ address }),
    })
        .then((response) => response.json())
        .then((data) => {
            deviceInput.value = data.address || "";
        })
        .catch((error) => console.error("Error saving device:", error));
}

function showLogs(project) {
    const modal = document.getElementById("logs-modal");
    const modalContent = document.getElementById("modal-logs-content");
    
    modal.classList.add("active");
    modalContent.textContent = "Loading logs...";
    
    fetch(`/api/logs?project=${encodeURIComponent(project)}`)
        .then((response) => {
            if (!response.ok) {
                return response.json().then((data) => {
                    throw new Error(data.error || "Failed to load logs");
                });
            }
            return response.json();
        })
        .then((data) => {
            modalContent.textContent = data.logs || "No logs available.";
        })
        .catch((error) => {
            modalContent.textContent = `Error: ${error.message}`;
        });
}

function closeLogsModal() {
    const modal = document.getElementById("logs-modal");
    modal.classList.remove("active");
}

refreshBtn.addEventListener("click", fetchProjects);
deviceSaveBtn.addEventListener("click", saveDevice);

document.getElementById("modal-close-btn").addEventListener("click", closeLogsModal);
document.getElementById("logs-modal").addEventListener("click", (e) => {
    if (e.target.id === "logs-modal") {
        closeLogsModal();
    }
});

function toggleInfoPanel() {
    const content = document.getElementById("info-panel-content");
    const icon = document.getElementById("info-toggle-icon");
    const isCollapsed = content.classList.contains("collapsed");
    
    if (isCollapsed) {
        content.classList.remove("collapsed");
        content.classList.add("expanded");
        icon.classList.remove("collapsed");
    } else {
        content.classList.remove("expanded");
        content.classList.add("collapsed");
        icon.classList.add("collapsed");
    }
}

function copyToClipboard(button, elementId) {
    const codeElement = document.getElementById(elementId);
    const text = codeElement.textContent.trim();
    
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add("copied");
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove("copied");
        }, 2000);
    }).catch((error) => {
        console.error("Failed to copy:", error);
        // Fallback for older browsers
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand("copy");
            const originalHTML = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i> Copied!';
            button.classList.add("copied");
            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.classList.remove("copied");
            }, 2000);
        } catch (err) {
            console.error("Fallback copy failed:", err);
        }
        document.body.removeChild(textArea);
    });
}

// Make copyToClipboard available globally for onclick handler
window.copyToClipboard = copyToClipboard;

document.getElementById("info-panel-toggle").addEventListener("click", toggleInfoPanel);

fetchProjects();
loadDevice();
setInterval(updateAllStatuses, 5000);
