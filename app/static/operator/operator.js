const state = {
  token: sessionStorage.getItem("signalsOperatorToken"),
  investigationId: null,
  polling: null,
};

const tokenDialog = document.getElementById("tokenDialog");
const tokenInput = document.getElementById("tokenInput");
const saveTokenButton = document.getElementById("saveTokenButton");
const launchButton = document.getElementById("launchButton");

function unlock() {
  if (state.token) {
    tokenDialog.classList.add("unlocked");
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

      if (["completed", "failed"].includes(job.status)) {
        clearInterval(state.polling);
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
