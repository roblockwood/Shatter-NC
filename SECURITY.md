# Security Policy

## Supported Versions

Security fixes are applied to the latest release on the `main` branch. Older tagged releases may not receive backports unless noted in release notes.

## Reporting a Vulnerability

If you discover a security issue, please **do not** open a public GitHub issue with exploit details.

Instead:

1. Use [GitHub private vulnerability reporting](https://github.com/roblockwood/Shatter-NC/security/advisories/new) if enabled for this repository, **or**
2. Email the maintainers with a description of the issue, steps to reproduce, and impact assessment.

We aim to acknowledge reports within a few business days and will coordinate disclosure and a fix before public details are published when appropriate.

## Sensitive Configuration

Shatter deployments require secrets such as database passwords, `SECRET_KEY`, and optional SMTP/Twilio credentials. Never commit `.env` files or backups (for example `.env.bak`) to version control. Use the provided `.env.example` and `.env.production.example` templates with values generated locally.
