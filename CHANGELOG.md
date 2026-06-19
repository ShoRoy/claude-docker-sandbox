# Changelog

All notable changes to claude-docker-sandbox.

## [v1.0] — 2026-06-19
- Initial release: minimal hardened Docker dev container for running Claude Code on WSL.
- `Dockerfile` — non-root ubuntu:22.04 baseline.
- `.devcontainer/devcontainer.json` — scoped bind mounts, `--cap-drop=ALL`,
  `no-new-privileges`, sized `noexec` tmpfs; auto-installs the Claude Code extension.
- `.claude/settings.json` — example tiered deny/ask/allow rules ("deny beats allow").
- `.claude/hooks/audit.py` — logs every Bash command to `.audit.log`.
- Companion to the article "Dockered Claude".
