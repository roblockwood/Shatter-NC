# Shatter-NC public install kit (repo contents)

This folder is intended to become the contents of a **separate public repo**, for example `roblockwood/shatter-nc-install`.

## What’s here

- `site/`: static generator app (GitHub Pages)\n  - Generates a `docker-compose.yml` and `.env` for a Komodo Stack.\n  - No backend; runs entirely in the user’s browser.\n- `.env.example`: minimal env template for the generated stack.\n- `docker-compose.packages.yml`: a reference “packages-only” compose (no source bind mounts).\n- `INSTALL.md`: install instructions centered on Docker + Komodo.\n
## Publishing (GitHub Pages)\n
Typical approach:\n
1. Create the public repo (example) `shatter-nc-install`.\n2. Copy the contents of this `install-kit/` folder into the root of that repo.\n3. Enable GitHub Pages for that repo:\n   - Settings → Pages\n   - Source: Deploy from a branch\n   - Branch: `main`\n   - Folder: `/site`\n
Your generator will be at the GitHub Pages URL for that repo.\n
