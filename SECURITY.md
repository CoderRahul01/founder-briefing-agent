# Security Policy

## Secret Management 🔒

Foundtel processes sensitive data including Gmail tokens and Stripe keys. To prevent accidental exposure:

- **Environment Variables**: Use a `.env` file for local development. Never commit this file.
- **Secrets Directory**: The `secrets/` directory is gitignored. Store `token.json` and `credentials.json` there.
- **GitHub Actions**: Production secrets are managed via GitHub Repository Secrets.

## Reporting a Vulnerability

If you discover a security vulnerability, please do NOT open a public issue. Instead, contact the maintainer directly or follow standard coordinated disclosure practices.

## Automated Scanning

This repository has GitHub Secret Scanning enabled. If you accidentally commit a secret, rotate it immediately and use tools like `git-filter-repo` (if possible) or contact GitHub support to purge the history.
