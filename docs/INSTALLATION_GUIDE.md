# Shatter Installation Guide

This guide walks through installing Shatter on **Windows**, **macOS**, or **Linux** using Docker Desktop. Choose the path that fits your use case:

- **Production / shop install** — run pre-built container images (recommended for operators)
- **Development install** — clone the repo and build locally (for contributors and advanced users)

---

## What You'll Need

- A computer on the same network as your Brother CNC(s), or one that can reach them
- **At least 4 GB RAM** (8 GB recommended)
- **About 10 GB free disk space** for Docker and Shatter
- **About 30 minutes** for first-time setup

---

## Table of Contents

1. [Install Docker Desktop](#1-install-docker-desktop)
2. [Production Install (Pre-built Images)](#2-production-install-pre-built-images)
3. [Development Install (From Source)](#3-development-install-from-source)
4. [Open Shatter and Add Machines](#4-open-shatter-and-add-machines)
5. [Stopping and Restarting](#5-stopping-and-restarting)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Install Docker Desktop

Shatter runs inside **Docker**. Install **Docker Desktop** for your operating system and leave defaults unless you know you need to change them.

### Windows

1. Download Docker Desktop: **[https://docs.docker.com/desktop/install/windows-install/](https://docs.docker.com/desktop/install/windows-install/)**
2. Run the installer. If it offers **WSL 2** (Windows Subsystem for Linux), accept it—Docker needs it.
3. Restart your PC when prompted.
4. Start **Docker Desktop** from the Start menu. Wait until it says “Docker Desktop is running”.

### macOS

1. Download Docker Desktop: **[https://docs.docker.com/desktop/install/mac-install/](https://docs.docker.com/desktop/install/mac-install/)**
   - **Apple Silicon (M1/M2/M3):** choose “Mac with Apple chip.”
   - **Intel:** choose “Mac with Intel chip.”
2. Open the downloaded `.dmg`, drag **Docker** into **Applications**.
3. Open **Docker** from Applications and wait until Docker Desktop is running.

### Linux

Install Docker Engine and Docker Compose plugin for your distribution. See **[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)**.

---

## 2. Production Install (Pre-built Images)

Use this path for shop-floor deployments. You need the compose file, environment template, and database init scripts—not a full development build.

### Step 1: Get the project files

**Option A — Git clone (recommended):**

```bash
git clone https://github.com/roblockwood/Shatter-NC.git
cd Shatter-NC
```

**Option B — GitHub Desktop:** clone [roblockwood/Shatter-NC](https://github.com/roblockwood/Shatter-NC) to a folder you can find later.

### Step 2: Configure environment

```bash
cp .env.production.example .env
```

Edit `.env` and set at minimum:

- `POSTGRES_PASSWORD` — strong database password
- `SECRET_KEY` — random string for session signing
- `CORS_ORIGINS` — JSON array of allowed browser origins (for example `["http://localhost:3000"]`)

Generate random values on macOS/Linux:

```bash
openssl rand -hex 32   # use for POSTGRES_PASSWORD and SECRET_KEY
```

### Step 3: Start Shatter

Pull pre-built images from GitHub Container Registry and start services:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Images are published as:

- `ghcr.io/roblockwood/shatter-nc/backend`
- `ghcr.io/roblockwood/shatter-nc/frontend`

The first start may take a few minutes while containers initialize and the database runs migrations.

**Windows / macOS shortcut:** you can also double-click **`start.bat`** (Windows) or **`start.command`** (macOS) after cloning. Those scripts create a `.env` from defaults and start the development compose stack—fine for trying Shatter locally, but production shops should prefer `docker-compose.prod.yml` as above.

---

## 3. Development Install (From Source)

For contributors or anyone who wants to build and hot-reload from source:

```bash
git clone https://github.com/roblockwood/Shatter-NC.git
cd Shatter-NC
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

See **[Development Guide](DEVELOPMENT_GUIDE.md)** for backend/frontend workflows, testing, and debugging.

---

## 4. Open Shatter and Add Machines

1. Open a web browser and go to: **http://localhost:3000**
2. You should see the Shatter dashboard.
3. Add your Brother CNC(s) using the on-screen instructions (name, IP address, and optional settings).

**Optional — access from another device on your network:**  
Use this machine’s IP address instead of `localhost`, e.g. `http://192.168.1.50:3000`. If it doesn’t load, check your firewall allows port 3000.

---

## 5. Stopping and Restarting

Use **Docker Desktop** or the terminal to stop and start Shatter. Your data is kept when you stop.

**Stop (production):**

```bash
docker compose -f docker-compose.prod.yml down
```

**Start again (production):**

```bash
docker compose -f docker-compose.prod.yml up -d
```

**Development compose:** replace `docker-compose.prod.yml` with `docker-compose.dev.yml`.

In Docker Desktop → **Containers**, you should see **shatter-db**, **shatter-backend**, and **shatter-frontend** (names may include `-prod` or `-dev` suffix depending on compose file).

---

## 6. Troubleshooting

**Docker says “Docker is not running”**  
Start Docker Desktop and wait until it’s fully up, then run the compose command again.

**“Cannot connect to the Docker daemon”**  
Ensure Docker Desktop is running. Try quitting and reopening Docker Desktop.

**Port already in use (e.g. 3000 or 8000)**  
Another program is using that port. Change `BACKEND_PORT` in `.env` or adjust port mappings in the compose file.

**Containers keep exiting**  
In Docker Desktop → **Containers**, open **Logs** for the failing container. Common causes: not enough memory, or invalid `.env` values.

**Browser shows “This site can’t be reached” at localhost:3000**  
Confirm **shatter-frontend** is running. Wait a minute after start, or try `http://127.0.0.1:3000`.

**Production image pull fails**  
Ensure you can reach `ghcr.io` and that images exist for the requested tag. See **[Docker Deployment Guide](DOCKER_DEPLOYMENT.md)** for registry authentication if needed.

---

## Summary

| Goal | Steps |
|------|--------|
| Shop / production | Clone repo → `cp .env.production.example .env` → edit secrets → `docker compose -f docker-compose.prod.yml up -d` |
| Development | Clone repo → `cp .env.example .env` → `docker compose -f docker-compose.dev.yml up -d` |
| Use Shatter | Open **http://localhost:3000** and add CNC machines |

For advanced deployment options, see **[Docker Deployment Guide](DOCKER_DEPLOYMENT.md)**. For contributing, see **[Development Guide](DEVELOPMENT_GUIDE.md)** and **[CONTRIBUTING.md](../CONTRIBUTING.md)**.
