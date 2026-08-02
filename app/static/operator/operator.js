const state = {
  token: sessionStorage.getItem("signalsOperatorToken"),
  investigationId: null,
  polling: null,
};

const tokenDialog = document.getElementById("tokenDialog");
const tokenInput = document.getElementById("tokenInput");
const saveTokenButton = document.getElementById("saveTokenButton");
const launchButton = document.getElementById("launchButton");
const refreshHistoryButton =
  document.getElementById("refreshHistoryButton");
const downloadMarkdown =
  document.getElementById("downloadMarkdown");
const downloadJson =
  document.getElementById("downloadJson");

function unlock() {
  if (state.token) {
    tokenDialog.classList.add("unlocked");
    loadHistory();
  }
}

saveTokenButton.addEventListener("click", () => {
  const token = tokenInput.value.trim();

  if (!token) {
    return;
  }

  state.token = token;
  sessionStorage.setItem("signalsOperatorToken", token);
  unlock();
});

unlock();

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Authorization": `Bearer ${state.token}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    sessionStorage.removeItem("signalsOperatorToken");
    state.token = null;
    tokenDialog.classList.remove("unlocked");
    throw new Error("Operator token was rejected.");
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status}: ${body}`);
  }

  return response.json();
}

launchButton.addEventListener("click", async () => {
  launchButton.disabled = true;
  launchButton.textContent = "Launching…";

  try {
    const job = await api("/api/operator/investigations", {
      method: "POST",
      body: JSON.stringify({
        scenario: document.getElementById("scenario").value,
        module_id: document.getElementById("moduleId").value,
        severity: document.getElementById("severity").value,
      }),
    });

    state.investigationId = job.investigation_id;

    document.getElementById("emptyState").classList.add("hidden");
    document.getElementById("workspace").classList.remove("hidden");

    render(job);
    startPolling();
  } catch (error) {
    alert(error.message);
  } finally {
    launchButton.disabled = false;
    launchButton.textContent = "Launch Investigation";
  }
});

function startPolling() {
  clearInterval(state.polling);

  state.polling = setInterval(async () => {
    if (!state.investigationId) {
      return;
    }

    try {
      const job = await api(
        `/api/operator/investigations/${state.investigationId}`
      );

      render(job);

      if (
        ["completed", "failed", "interrupted"].includes(job.status)
      ) {
        clearInterval(state.polling);
        loadHistory();
      }
    } catch (error) {
      console.error(error);
    }
  }, 1500);
}

function render(job) {
  setText("jobStatus", formatStatus(job.status));
  setText("investigationId", job.investigation_id);
  setText("incidentId", job.incident?.incident_id || "Pending");
  setText("affectedModule", job.incident?.module_id || job.module_id);

  renderIncident(job.incident);
  renderGrafanaLinks(job.grafana);
  renderTimeline(job.timeline || []);

  document.getElementById("report").textContent =
    job.report ||
    (job.error
      ? `${job.error.type}: ${job.error.message}`
      : "Gemini report will appear when the investigation completes.");

  const actions = document.getElementById("reportActions");

  if (job.report_files) {
    actions.classList.remove("hidden");

    downloadMarkdown.onclick = () =>
      downloadReport(job.investigation_id, "markdown");

    downloadJson.onclick = () =>
      downloadReport(job.investigation_id, "json");
  } else {
    actions.classList.add("hidden");
  }
}

function renderIncident(incident) {
  const container = document.getElementById("incidentDetails");
  const badge = document.getElementById("severityBadge");

  if (!incident) {
    container.textContent = "Waiting for synthetic incident creation…";
    badge.textContent = "Pending";
    return;
  }

  badge.textContent = incident.severity.toUpperCase();

  container.innerHTML = [
    row("Title", incident.title),
    row("Status", incident.status),
    row("Module", incident.module_id),
    row("Scenario", incident.telemetry_labels?.scenario || "—"),
    row("Synthetic", String(incident.synthetic)),
    row("Summary", incident.summary),
  ].join("");
}

function row(label, value) {
  return `
    <div class="detail-row">
      <span>${escapeHtml(label)}</span>
      <span>${escapeHtml(value ?? "—")}</span>
    </div>
  `;
}

function renderGrafanaLinks(links) {
  const container = document.getElementById("grafanaLinks");

  if (!links) {
    container.innerHTML =
      '<span class="muted">Links will appear after incident creation.</span>';
    return;
  }

  container.innerHTML = `
    <a class="evidence-link" href="${links.dashboard}" target="_blank">
      Open Signals Platform dashboard
    </a>
    <a class="evidence-link"
       href="${links.prometheus_explore}" target="_blank">
      Open Prometheus evidence
    </a>
    <a class="evidence-link"
       href="${links.loki_explore}" target="_blank">
      Open Loki investigation timeline
    </a>
  `;
}

function renderTimeline(events) {
  const timeline = document.getElementById("timeline");
  const toolCount = document.getElementById("toolCount");

  toolCount.textContent = `${events.length} events`;

  timeline.innerHTML = events.map((event) => {
    const failed =
      event.outcome === "failure" ||
      event.event === "tool_failed" ||
      event.event === "investigation_failed";

    const title = event.tool_name
      ? `${formatStatus(event.event)} · ${event.tool_name}`
      : formatStatus(event.event);

    return `
      <li class="${failed ? "failure" : ""}">
        <div class="timeline-title">${escapeHtml(title)}</div>
        <div class="timeline-meta">
          ${escapeHtml(formatTime(event.timestamp))}
          ${event.duration_seconds
            ? ` · ${event.duration_seconds}s`
            : ""}
        </div>
      </li>
    `;
  }).join("");
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function formatStatus(value = "") {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, character => character.toUpperCase());
}

function formatTime(value) {
  if (!value) {
    return "";
  }

  return new Date(value).toLocaleTimeString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


refreshHistoryButton.addEventListener("click", loadHistory);

async function loadHistory() {
  if (!state.token) {
    return;
  }

  try {
    const payload = await api("/api/operator/investigations");
    renderHistory(payload.investigations || []);
  } catch (error) {
    console.error(error);
  }
}

function renderHistory(investigations) {
  const container = document.getElementById("historyList");

  if (!investigations.length) {
    container.innerHTML =
      '<p class="muted">No stored investigations yet.</p>';
    return;
  }

  container.innerHTML = investigations.map(job => `
    <article class="history-item">
      <div class="history-value">
        <span class="history-label">Investigation</span>
        ${escapeHtml(job.investigation_id)}
      </div>

      <div class="history-value">
        <span class="history-label">Incident</span>
        ${escapeHtml(job.incident?.incident_id || "—")}
      </div>

      <div class="history-value">
        <span class="history-label">Module</span>
        ${escapeHtml(job.incident?.module_id || job.module_id || "—")}
      </div>

      <div class="history-value">
        <span class="history-label">Status</span>
        <span class="history-status ${escapeHtml(job.status)}">
          ${escapeHtml(formatStatus(job.status))}
        </span>
      </div>

      <button
        type="button"
        data-investigation-id="${escapeHtml(job.investigation_id)}"
      >
        Open
      </button>
    </article>
  `).join("");

  container.querySelectorAll("[data-investigation-id]")
    .forEach(button => {
      button.addEventListener("click", async () => {
        const investigationId =
          button.dataset.investigationId;

        const job = await api(
          `/api/operator/investigations/${investigationId}`
        );

        state.investigationId = investigationId;

        document.getElementById("emptyState")
          .classList.add("hidden");

        document.getElementById("workspace")
          .classList.remove("hidden");

        render(job);

        window.scrollTo({
          top: document.getElementById("workspace").offsetTop - 20,
          behavior: "smooth",
        });

        if (
          !["completed", "failed", "interrupted"]
            .includes(job.status)
        ) {
          startPolling();
        }
      });
    });
}

async function downloadReport(investigationId, format) {
  const response = await fetch(
    `/api/operator/investigations/${investigationId}` +
    `/reports/${format}`,
    {
      headers: {
        "Authorization": `Bearer ${state.token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Report download failed: ${response.status}`);
  }

  const blob = await response.blob();
  const disposition =
    response.headers.get("Content-Disposition") || "";

  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match
    ? match[1]
    : `${investigationId}.${format === "json" ? "json" : "md"}`;

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  URL.revokeObjectURL(url);
}

