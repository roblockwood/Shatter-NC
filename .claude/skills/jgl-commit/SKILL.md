---
name: jgl-commit
description: Stage, commit, and push changes to GitHub with a meaningful message. Use when the user says "commit", "/jgl-commit", "save my work", "push", or "checkpoint".
allowed-tools: Bash, Read, Grep, Glob
---

# Commit

Save the current state of the project to git and push to GitHub.

1. Run `git status` to see what changed.
2. Stage all relevant changes. **Do not stage** files that look like secrets — warn the user if any are present:
   - `.env`, `.env.*` files
   - Files containing credentials, API keys, or passwords
   - Docker environment files (`.env.example` is fine, actual `.env` is not)
   - `kaeser-sc2-api.env` or similar machine credential files
3. Write a short, meaningful commit message that describes what changed and why. Follow the project's conventional commit format:
   ```
   feat: add tool validation for ATC magazine
   fix: correct FTP sync exclusion rule for NC files
   docs: update API reference for machine endpoints
   refactor: extract telnet lock into standalone module
   ```
   Not "update files" or "fix stuff."
4. Commit.
5. Push to the remote. If no remote is set up, tell the user.

## If nothing changed

If `git status` shows no changes, say so. Don't create an empty commit.
