# Shatter Installation Guide

This guide walks you through installing Shatter on **Windows** or **macOS** using Docker Desktop. It’s written so a machinist or shop operator can follow it without prior Docker or development experience. You’ll use **GitHub Desktop** to get the project and run Shatter **from source** (Docker builds the app from the cloned code).

---

## What You’ll Need

- A computer on the same network as your Brother CNC(s), or one that can reach them.
- **At least 4 GB RAM** (8 GB recommended).
- **About 10 GB free disk space** for Docker and Shatter.
- **About 30 minutes** for first-time setup.

---

## Table of Contents

1. [Install Docker Desktop](#1-install-docker-desktop)
2. [Get the Project with GitHub Desktop](#2-get-the-project-with-github-desktop)
3. [Start Shatter](#3-start-shatter)
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
4. Start **Docker Desktop** from the Start menu. Wait until it says “Docker Desktop is running” (whale icon in the system tray).
5. **Optional:** Sign in with a Docker Hub account, or skip—Shatter does not require it.

**Tip:** If the installer says “WSL 2 installation is incomplete,” follow the link it gives to install/update WSL 2, then run the Docker installer again.

### macOS

1. Download Docker Desktop: **[https://docs.docker.com/desktop/install/mac-install/](https://docs.docker.com/desktop/install/mac-install/)**
   - **Apple Silicon (M1/M2/M3):** choose “Mac with Apple chip.”
   - **Intel:** choose “Mac with Intel chip.”
2. Open the downloaded `.dmg`, drag **Docker** into **Applications**.
3. Open **Docker** from Applications. Accept the terms and grant any requested permissions.
4. Wait until the menu bar shows “Docker Desktop is running.”

---

## 2. Get the Project with GitHub Desktop

Shatter’s code lives in a **private GitHub repository**. The repo owner must add your GitHub account as a collaborator (or give access via an organization). Then use GitHub Desktop to clone the project—no terminal or passwords to type.

1. **Install GitHub Desktop**  
   Download and install: **[https://desktop.github.com/](https://desktop.github.com/)**

2. **Sign in to GitHub**  
   Open GitHub Desktop → **File** → **Options** → **Accounts** → **Sign in** to GitHub. Use your GitHub username and password (or sign in in the browser if it offers that).

3. **Clone the repo**  
   - **File** → **Clone repository**.
   - Choose the **GitHub.com** tab.
   - Find **Shatter-NC** (or the repo name the owner gave you). Select it.
   - Under “Local path,” pick a folder (e.g. `Documents` or `C:\Users\YourName\Documents`). Remember this path.
   - Click **Clone**. Wait until it finishes; you’ll see the list of project files.

4. **Where is the project?**  
   The project will be in a folder like:
   - **Windows:** `C:\Users\YourName\Documents\Shatter-NC`
   - **macOS:** `/Users/yourusername/Documents/Shatter-NC`

You’ll start Shatter from this folder in [Step 3](#3-start-shatter).

**To get updates later:** In GitHub Desktop, select the repo and click **Fetch origin** / **Pull origin** when the owner tells you there’s a new version.

---

## 3. Start Shatter

Shatter includes a **Start** script that sets everything up and starts Docker. You don't need to use a terminal or generate any passwords—the script creates a `.env` file the first time (with a random database password) and starts the app.

**Windows**

1. Open **File Explorer** and go to the `Shatter-NC` folder (where you cloned the project).
2. Double-click **start.bat**.
3. A window will open. The first time, it will say "Creating .env from defaults…" and create a `.env` file with a random database password. Then it runs Docker.
4. Wait until the window says "Shatter is starting. Open http://localhost:3000…" (the first time can take several minutes while Docker downloads and builds).
5. You can close the window after it finishes.

**macOS**

1. Open **Finder** and go to the `Shatter-NC` folder (where you cloned the project).
2. Double-click **start.command**.
3. If macOS says the file is from an unidentified developer: right-click **start.command** → **Open** → **Open** in the dialog. You only need to do that once.
4. A Terminal window will open. The first time, it will say "Creating .env from defaults…" and create a `.env` file with a random database password. Then it runs Docker.
5. Wait until it says "Shatter is starting. Open http://localhost:3000…" (the first time can take several minutes).
6. Press any key to close the window, or leave it open.

**Do I need to create or edit .env or generate passkeys?**  
No. The script creates `.env` for you the first time and puts a random database password in it. You don't need to generate or type any passwords. If you ever want to change the database password or other settings, you can edit the `.env` file in the project folder with a text editor.

**Check that everything is running**  
Open **Docker Desktop** → **Containers**. You should see **shatter-db**, **shatter-backend**, and **shatter-frontend** running. If any show "Exited" or "Restarting," see [Troubleshooting](#6-troubleshooting).

---

## 4. Open Shatter and Add Machines

1. Open a web browser and go to: **http://localhost:3000**
2. You should see the Shatter dashboard.
3. Add your Brother CNC(s) using the on-screen instructions (name, IP address, and optional settings). Shatter will then poll and show status.

**Optional – access from another device on your network:**  
Use this machine’s IP address instead of `localhost`, e.g. `http://192.168.1.50:3000`. If it doesn’t load, check your firewall allows port 3000.

---

## 5. Stopping and Restarting

Use **Docker Desktop** to stop and start Shatter. Your data is kept when you stop.

**Stop Shatter**

1. Open **Docker Desktop**.
2. In the left sidebar, click **Containers**.
3. Find the Shatter containers (**shatter-db**, **shatter-backend**, **shatter-frontend**). They may appear under a **shatter** group.
4. Select the group (or each container). Click **Stop** (square icon) to stop them.

**Start Shatter again**

1. Open **Docker Desktop** → **Containers**.
2. Find the stopped Shatter containers (shatter-db, shatter-backend, shatter-frontend).
3. Select the group (or each container). Click **Start** (play icon) to start them again.

**View logs (e.g. to diagnose issues)**

1. Open **Docker Desktop** → **Containers**.
2. Click a container name (e.g. **shatter-backend** or **shatter-frontend**).
3. Open the **Logs** tab to see its output.

---

## 6. Troubleshooting

**Docker says “Docker is not running”**  
Start Docker Desktop and wait until it’s fully up, then double-click **start.bat** (Windows) or **start.command** (macOS) again.

**“Cannot connect to the Docker daemon”**  
Ensure Docker Desktop is running. If it is, try quitting and reopening Docker Desktop, then run the Start script again.

**Port already in use (e.g. 3000 or 8000)**  
Another program is using that port. Either close that program or change the port in `.env` (e.g. `BACKEND_PORT`, and frontend port in `docker-compose.dev.yml` if you need to).

**Containers keep exiting**  
In Docker Desktop → **Containers**, click the container that’s exiting (e.g. **shatter-backend**) and open the **Logs** tab. Check the end of the output for errors. Common causes: not enough memory, or a bad `.env` (e.g. typo in a variable). Fix the cause, then stop the Shatter containers and start them again (Section 5).


**Backend logs show start-dev.sh: no such file or directory**  
Pull the latest project (GitHub Desktop → **Pull origin**), then rebuild: in a terminal in the project folder run `docker compose -f docker-compose.dev.yml build backend --no-cache` then `docker compose -f docker-compose.dev.yml up -d`. After that, use the Start script or Docker Desktop as usual.

**“Permission denied” or “Access denied” when cloning**  
Your GitHub account doesn’t have access to the repo. Ask the repo owner to add you as a collaborator, then try cloning again in GitHub Desktop.

**Browser shows “This site can’t be reached” at localhost:3000**  
In Docker Desktop → **Containers**, check that **shatter-frontend** is running (not stopped). If it is running, try `http://127.0.0.1:3000` or stop and start the Shatter containers again and wait a minute for the dev server to start.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Install Docker Desktop (Windows or macOS). |
| 2 | Install GitHub Desktop, sign in to GitHub, clone the Shatter repo. |
| 3 | Double-click **start.bat** (Windows) or **start.command** (macOS) in the project folder. The script creates .env and starts Shatter; no passkeys to generate. |
| 4 | Open **http://localhost:3000** and add your CNC machines. |
| 5 | To stop: Docker Desktop → Containers → select Shatter containers → Stop. To start again: Containers → select them → Start. |

For production deployment or other compose options, see [Docker Deployment Guide](DOCKER_DEPLOYMENT.md). For development workflows and contributing, see [Development Guide](DEVELOPMENT_GUIDE.md).
