function qs(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element: ${id}`);
  return el;
}

function genSecretKeyHex(bytes = 32) {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => b.toString(16).padStart(2, "0")).join("");
}

function buildEnv(cfg) {
  const lines = [];
  lines.push("# Shatter-NC runtime configuration");
  lines.push("# Generated locally. Do not commit this file.");
  lines.push("");
  lines.push(`POSTGRES_PASSWORD=${cfg.POSTGRES_PASSWORD}`);
  lines.push(`SECRET_KEY=${cfg.SECRET_KEY}`);
  if (cfg.KAESER_ENABLED) {
    lines.push("");
    lines.push("# Kaeser (beta) - optional");
    lines.push(`KAESER_ADDRESS=${cfg.KAESER_ADDRESS}`);
    lines.push(`KAESER_USERNAME=${cfg.KAESER_USERNAME}`);
    lines.push(`KAESER_PASSWORD=${cfg.KAESER_PASSWORD}`);
    lines.push(`MQTT_TOPIC_ROOT=${cfg.MQTT_TOPIC_ROOT}`);
    lines.push(`KAESER_LOG_LEVEL=${cfg.KAESER_LOG_LEVEL}`);
  }
  lines.push("");
  return lines.join("\n");
}

function buildEnvPreview(cfg) {
  const lines = [];
  lines.push("# Shatter-NC runtime configuration");
  lines.push("# Generated locally. Do not commit this file.");
  lines.push("");
  // Keep preview style simple and consistent with production feel.
  lines.push(`POSTGRES_PASSWORD=${cfg.POSTGRES_PASSWORD || "CHANGEME_STRONG_PASSWORD"}`);
  lines.push(`SECRET_KEY=${cfg.SECRET_KEY || "CHANGEME_GENERATE_RANDOM"}`);
  if (cfg.KAESER_ENABLED) {
    lines.push("");
    lines.push("# Kaeser (beta) - optional");
    lines.push(`KAESER_ADDRESS=${cfg.KAESER_ADDRESS || "https://YOUR_KAESER_SC2_HOST"}`);
    lines.push(`KAESER_USERNAME=${cfg.KAESER_USERNAME || "CHANGEME"}`);
    lines.push(`KAESER_PASSWORD=${cfg.KAESER_PASSWORD ? "********" : "CHANGEME"}`);
    lines.push(`MQTT_TOPIC_ROOT=${cfg.MQTT_TOPIC_ROOT || "kaeser-sc2-01"}`);
    lines.push(`KAESER_LOG_LEVEL=${cfg.KAESER_LOG_LEVEL || "info"}`);
  }
  lines.push("");
  return lines.join("\n");
}

function buildCompose(cfg) {
  // Packages-only compose:
  // - no bind mounts that require a private repo checkout
  // - backend image includes /app/migrations and runs migrations on startup
  const backendImage = `ghcr.io/roblockwood/shatter-nc-install/backend:latest`;
  const frontendImage = `ghcr.io/roblockwood/shatter-nc-install/frontend:latest`;
  const kaeserSidecarImage = `ghcr.io/roblockwood/shatter-nc-install/kaeser-sc2-api:latest`;

  const kaeserProfilesLine = cfg.KAESER_ENABLED ? "" : '    profiles: ["kaeser"]\n';

  return `services:
  kaeser-sc2-api:
${kaeserProfilesLine}` +
`    image: ${kaeserSidecarImage}
    container_name: shatter-kaeser-sc2-api-prod
    restart: unless-stopped
    environment:
      # Required (Kaeser SC2 portal)
      KAESER_ADDRESS: \${KAESER_ADDRESS:-}
      KAESER_USERNAME: \${KAESER_USERNAME:-}
      KAESER_PASSWORD: \${KAESER_PASSWORD:-}
      # Optional (publish to MQTT broker)
      MQTT_HOST: \${MQTT_HOST:-mqtt}
      MQTT_PORT: \${MQTT_PORT:-1883}
      MQTT_USER: \${MQTT_USER:-}
      MQTT_PASS: \${MQTT_PASS:-}
      MQTT_TOPIC_ROOT: \${MQTT_TOPIC_ROOT:-kaeser-sc2-01}
      LOG_LEVEL: \${KAESER_LOG_LEVEL:-info}
    ports:
      - "\${KAESER_SC2_API_PORT:-3004}:3004"
    depends_on:
      - mqtt
    networks:
      - shatter-network

  mqtt:
    image: eclipse-mosquitto:2
    container_name: shatter-mqtt-prod
    restart: unless-stopped
    ports:
      - "\${MQTT_PORT:-1883}:1883"
    networks:
      - shatter-network

  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: shatter-db-prod
    restart: unless-stopped
    environment:
      POSTGRES_DB: shatter
      POSTGRES_USER: shatter_user
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shatter_user -d shatter"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - shatter-network

  backend:
    image: ${backendImage}
    container_name: shatter-backend-prod
    restart: unless-stopped
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: shatter
      POSTGRES_USER: shatter_user
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
      LOG_LEVEL: \${LOG_LEVEL:-WARNING}
      DEFAULT_POLL_INTERVAL: \${DEFAULT_POLL_INTERVAL:-5}
      MQTT_BROKER_HOST: \${MQTT_BROKER_HOST:-mqtt}
      MQTT_BROKER_PORT: \${MQTT_BROKER_PORT:-1883}
      MQTT_USER: \${MQTT_USER:-}
      MQTT_PASSWORD: \${MQTT_PASS:-}
      COMPRESSOR_REST_REFRESH_SECONDS: \${COMPRESSOR_REST_REFRESH_SECONDS:-10}
      COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS: \${COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS:-1}
      COMPRESSOR_STATUS_SAMPLES_RAW_DAYS: \${COMPRESSOR_STATUS_SAMPLES_RAW_DAYS:-14}
      KAESER_SIDECAR_ENV_DIR: \${KAESER_SIDECAR_ENV_DIR:-/docker/generated}
      SECRET_KEY: \${SECRET_KEY}
      CORS_ORIGINS: '["*"]'
    volumes:
      - generated_data:/docker/generated
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      mqtt:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "--max-time", "10", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 15s
      retries: 3
      start_period: 40s
    networks:
      - shatter-network

  frontend:
    image: ${frontendImage}
    container_name: shatter-frontend-prod
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - shatter-network

volumes:
  postgres_data:
    driver: local
  generated_data:
    driver: local

networks:
  shatter-network:
    driver: bridge
`;
}

function readConfig() {
  const cfg = {
    POSTGRES_PASSWORD: qs("pgPassword").value,
    SECRET_KEY: qs("secretKey").value,
    KAESER_ENABLED: Boolean(document.getElementById("kaeserEnabled")?.checked),
    KAESER_ADDRESS: document.getElementById("kaeserAddress")?.value?.trim() || "",
    KAESER_USERNAME: document.getElementById("kaeserUsername")?.value?.trim() || "",
    KAESER_PASSWORD: document.getElementById("kaeserPassword")?.value || "",
    MQTT_TOPIC_ROOT: document.getElementById("kaeserMqttTopicRoot")?.value?.trim() || "kaeser-sc2-01",
    KAESER_LOG_LEVEL: document.getElementById("kaeserLogLevel")?.value?.trim() || "info",
  };

  const errors = [];
  if (!cfg.POSTGRES_PASSWORD) errors.push("POSTGRES_PASSWORD is required");
  if (!cfg.SECRET_KEY) errors.push("SECRET_KEY is required");
  if (cfg.KAESER_ENABLED) {
    if (!cfg.KAESER_ADDRESS) errors.push("KAESER_ADDRESS is required when Kaeser is enabled");
    if (!cfg.KAESER_USERNAME) errors.push("KAESER_USERNAME is required when Kaeser is enabled");
    if (!cfg.KAESER_PASSWORD) errors.push("KAESER_PASSWORD is required when Kaeser is enabled");
  }

  return { cfg, errors };
}

function render() {
  const { cfg, errors } = readConfig();
  const envOut = qs("envOut");
  const composeOut = qs("composeOut");

  // Step enablement / gating
  const osSelected = Boolean(qs("os").value);
  const pgOk = Boolean(qs("pgPassword").value);
  const keyOk = Boolean(qs("secretKey").value);

  const step2 = document.getElementById("step2");
  const step3 = document.getElementById("step3");
  const step4 = document.getElementById("step4");
  const step5 = document.getElementById("step5");
  const step6 = document.getElementById("step6");
  const step7 = document.getElementById("step7");
  const step8 = document.getElementById("step8");
  const step9 = document.getElementById("step9");
  const state = window.__shatterInstallState || (window.__shatterInstallState = {
    step1Confirmed: false,
    step2Confirmed: false,
    step3Confirmed: false,
    kaeserConfirmed: false,
    pgConfirmed: false,
    envConfirmed: false,
    composeConfirmed: false,
    envEdited: false,
    composeEdited: false,
  });

  const enablePanel = (el, enabled) => {
    if (!el) return;
    el.classList.toggle("disabled", !enabled);
    el.setAttribute("aria-disabled", enabled ? "false" : "true");
  };

  enablePanel(step2, state.step1Confirmed);
  enablePanel(step3, state.step2Confirmed);
  enablePanel(step4, state.step3Confirmed);
  enablePanel(step5, state.kaeserConfirmed);
  enablePanel(step6, state.pgConfirmed);
  enablePanel(step7, keyOk);
  enablePanel(step8, keyOk && state.envConfirmed);
  enablePanel(step9, keyOk && state.composeConfirmed);

  // Next button enablement
  const toStep2 = document.getElementById("toStep2");
  const toStep3 = document.getElementById("toStep3");
  const toStep4 = document.getElementById("toStep4");
  const toStep5 = document.getElementById("toStep5");
  const toStep6 = document.getElementById("toStep6");
  if (toStep2) toStep2.disabled = !osSelected;
  if (toStep3) toStep3.disabled = !state.step1Confirmed;
  if (toStep4) toStep4.disabled = !state.step2Confirmed;
  if (toStep6) toStep6.disabled = !pgOk;

  // Always show previews (placeholders) even before unlocked.
  if (!state.envEdited) envOut.value = errors.length ? buildEnvPreview(cfg) : buildEnv(cfg);
  if (!state.composeEdited) composeOut.value = buildCompose(cfg);
}

function renderOsNote() {
  const os = qs("os").value;
  const el = qs("osNote");
  const lines = [];

  if (!os) {
    el.textContent = "Select your OS to see the install instructions.";
    return;
  }

  if (os === "mac") {
    lines.push("macOS: Docker Engine runs inside a VM. Use Docker Desktop or another Docker-compatible runtime, then verify `docker run --rm hello-world`.");
  } else if (os === "win") {
    lines.push("Windows: Use Docker Desktop with WSL2 backend (recommended). Verify `docker run --rm hello-world` in the same environment you will run Komodo/Compose from.");
  } else if (os === "linux") {
    lines.push("Linux: Install Docker Engine from the official docs for your distro. Consider adding your user to the `docker` group so you can run Docker without sudo.");
  }

  const url =
    os === "mac" || os === "win"
      ? "https://www.docker.com/products/docker-desktop/"
      : "https://docs.docker.com/engine/install/";

  el.innerHTML = [
    `<div>Docker install: <a href="${url}" target="_blank" rel="noopener noreferrer"><code>${url}</code></a></div>`,
    `<div>Verify: <code>docker run --rm hello-world</code></div>`,
    `<div style="margin-top: 8px">${lines.join(" ")}</div>`,
  ].join("");
}

async function copyText(text) {
  await navigator.clipboard.writeText(text);
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function bind() {
  const cfgInputs = [
    "kaeserEnabled",
    "kaeserAddress",
    "kaeserUsername",
    "kaeserPassword",
    "kaeserMqttTopicRoot",
    "kaeserLogLevel",
    "pgPassword",
    "secretKey",
  ];
  cfgInputs.forEach((id) => qs(id).addEventListener("input", render));
  // checkbox uses "change" more reliably than "input"
  document.getElementById("kaeserEnabled")?.addEventListener("change", render);

  qs("envOut").addEventListener("input", () => {
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.envEdited = true;
  });
  qs("composeOut").addEventListener("input", () => {
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.composeEdited = true;
  });

  const setOs = (value) => {
    qs("os").value = value;
    ["osBtnMac", "osBtnWin", "osBtnLinux"].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.classList.toggle("selected", btn.getAttribute("data-os") === value);
    });
    renderOsNote();
    render();
  };

  // OS buttons (Shatter-style single-select)
  ["osBtnMac", "osBtnWin", "osBtnLinux"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", () => setOs(btn.getAttribute("data-os") || ""));
  });

  qs("genSecret").addEventListener("click", () => {
    qs("secretKey").value = genSecretKeyHex(32);
    render();
    document.getElementById("step7")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  qs("copyEnv").addEventListener("click", async () => {
    await copyText(qs("envOut").value);
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.envConfirmed = true;
    render();
    document.getElementById("step8")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  qs("copyCompose").addEventListener("click", async () => {
    await copyText(qs("composeOut").value);
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.composeConfirmed = true;
    render();
    document.getElementById("step9")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Step navigation (scroll)
  qs("toStep2").addEventListener("click", () => {
    if (!qs("os").value) {
      document.getElementById("osBtnMac")?.focus();
      return;
    }
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.step1Confirmed = true;
    render();
    scrollTo("step2");
  });
  qs("toStep3").addEventListener("click", () => {
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.step2Confirmed = true;
    render();
    scrollTo("step3");
  });
  qs("toStep4").addEventListener("click", () => {
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.step3Confirmed = true;
    render();
    scrollTo("step4");
  });
  document.getElementById("toStep5")?.addEventListener("click", () => {
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.kaeserConfirmed = true;
    render();
    scrollTo("step5");
  });
  document.getElementById("toStep6")?.addEventListener("click", () => {
    if (!qs("pgPassword").value) {
      qs("pgPassword").focus();
      return;
    }
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.pgConfirmed = true;
    render();
    scrollTo("step6");
  });

  render();
  renderOsNote();
  // No default OS selection; user must click one.
}

bind();

