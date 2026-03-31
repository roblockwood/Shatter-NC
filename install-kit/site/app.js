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
  lines.push("");
  return lines.join("\n");
}

function buildCompose(cfg) {
  // Packages-only compose:
  // - no bind mounts that require a private repo checkout
  // - backend image includes /app/migrations and runs migrations on startup
  const backendImage = `ghcr.io/roblockwood/shatter-nc/backend:latest`;
  const frontendImage = `ghcr.io/roblockwood/shatter-nc/frontend:latest`;

  return `services:
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
      SECRET_KEY: \${SECRET_KEY}
      CORS_ORIGINS: '["*"]'
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
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

networks:
  shatter-network:
    driver: bridge
`;
}

function readConfig() {
  const cfg = {
    POSTGRES_PASSWORD: qs("pgPassword").value,
    SECRET_KEY: qs("secretKey").value,
  };

  const errors = [];
  if (!cfg.POSTGRES_PASSWORD) errors.push("POSTGRES_PASSWORD is required");
  if (!cfg.SECRET_KEY) errors.push("SECRET_KEY is required");

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
  const state = window.__shatterInstallState || (window.__shatterInstallState = {
    step1Confirmed: false,
    step2Confirmed: false,
    step3Confirmed: false,
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
  enablePanel(step5, state.pgConfirmed);
  enablePanel(step6, keyOk);
  enablePanel(step7, keyOk && state.envConfirmed);
  enablePanel(step8, keyOk && state.composeConfirmed);

  // Next button enablement
  const toStep2 = document.getElementById("toStep2");
  const toStep3 = document.getElementById("toStep3");
  const toStep4 = document.getElementById("toStep4");
  const toStep5 = document.getElementById("toStep5");
  if (toStep2) toStep2.disabled = !osSelected;
  if (toStep3) toStep3.disabled = !state.step1Confirmed;
  if (toStep4) toStep4.disabled = !state.step2Confirmed;
  if (toStep5) toStep5.disabled = !pgOk;

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
  const cfgInputs = ["pgPassword", "secretKey"];
  cfgInputs.forEach((id) => qs(id).addEventListener("input", render));

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
    document.getElementById("step6")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  qs("copyEnv").addEventListener("click", async () => {
    await copyText(qs("envOut").value);
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.envConfirmed = true;
    render();
    document.getElementById("step7")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  qs("copyCompose").addEventListener("click", async () => {
    await copyText(qs("composeOut").value);
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.composeConfirmed = true;
    render();
    document.getElementById("step8")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
    if (!qs("pgPassword").value) {
      qs("pgPassword").focus();
      return;
    }
    const state = window.__shatterInstallState || (window.__shatterInstallState = {});
    state.pgConfirmed = true;
    render();
    scrollTo("step5");
  });

  render();
  renderOsNote();
  // No default OS selection; user must click one.
}

bind();

