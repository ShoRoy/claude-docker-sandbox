# claude-docker-sandbox

A small, sensibly-hardened **Docker dev container for running an AI coding agent
(Claude Code)** — so it can edit your codebase freely but can't touch your host
machine or read the files it has no business reading. Built and documented for
Windows + WSL; the config is plain Docker and runs anywhere.

Clone it, point it at your project, and you have a fail-safe box in about ten minutes.

> Full write-up — the threat model and the reasoning behind every line:
> **[Dockered Claude](ARTICLE_URL)** *(replace with the published article link)*.

---

## What this is

A dev container built on one idea: **an asymmetric wall.** You reach into the box
freely from the host; the agent can't reach back out. It sees only the folders you
mount, runs as a non-root user, can't escalate privileges, and can't reach the
Docker daemon. Inside, three rule layers keep sensitive files compilable but
unreadable to the agent:

| Layer | Lives in | Enforced by |
|---|---|---|
| **Hard** | `.devcontainer/devcontainer.json` + `Dockerfile` | the OS / kernel |
| **Semi-hard** | `.claude/settings.json` | Claude Code's permission engine |
| **Soft** | `CLAUDE.md` (your project) | the model's own compliance |

## Prerequisites

**Windows 10/11 + WSL 2 (Ubuntu), Docker Desktop (WSL 2 backend, integration on), and VS Code + the Dev Containers extension.** The Claude Code extension is auto-installed inside the container. Keep the project on the WSL filesystem (`~/...`), not `/mnt/c`.

First time with this stack? **[SETUP.md](SETUP.md)** is the full walkthrough (install, the WSL "open from WSL / `docker ps` just works" gotchas, troubleshooting).

> **Built for Windows + WSL.** On macOS or native Linux you don't need WSL — run Docker Desktop (mac) or Docker Engine (Linux) and skip the WSL notes. The rest is unchanged: the `Dockerfile`, `.devcontainer/devcontainer.json`, and `.claude/` rules are plain Docker + Claude Code config, and the Claude Code extension with browser/subscription sign-in (no API key) works the same in VS Code on all three platforms.

## Quickstart

```bash
git clone https://github.com/ShoRoy/claude-docker-sandbox.git
cd claude-docker-sandbox
mkdir -p workspace config           # workspace/ = your code; config/ = container home
# put (or symlink) your project under workspace/
code .                              # then: "Dev Containers: Reopen in Container"
```

Without VS Code:

```bash
docker build -t claude-sandbox .
docker run --rm -it \
  -v "$PWD/workspace:/workspace" -v "$PWD/config:/home/claudeuser" \
  --tmpfs /tmp:rw,size=4g,mode=1777,noexec,nosuid,nodev \
  --tmpfs /run:rw,size=64m,mode=755,noexec,nosuid,nodev \
  --cap-drop=ALL --security-opt no-new-privileges \
  --user claudeuser -w /workspace claude-sandbox bash
```

## Edit these for your project

1. **`.claude/settings.json`** — the full tiered deny template (tool-level → Bash
   readers → writers/movers → archive/exfil → scripting interpreters) for two example
   targets. It's *generated*, so don't hand-edit it — edit the `RESTRICTED_FOLDERS` /
   `RESTRICTED_FILES` lists at the top of **`.claude/generate_deny_rules.py`** (set them
   to the files in *your* tree the agent must not read) and run
   `python3 .claude/generate_deny_rules.py --write`. `deny` beats `allow`, so the build
   still compiles those files (a child `gfortran`/`gcc` reads them as you) while the
   agent's own `cat`/`Read` is refused. It's pattern-based, so extend the tool lists as
   your paths need — and lean on the container (Layer 1) + `CLAUDE.md` (Layer 3) for what
   patterns can't catch.
2. **`.devcontainer/devcontainer.json`** — adjust the `mounts` to expose only what
   the agent should touch; mark read-only trees with `,readonly`.
3. **`CLAUDE.md`** (create in your project) — the behavioral contract: list the
   restricted paths and ask the agent to treat them as opaque and not route around
   the rules. (Template in the article.)

The audit hook (`.claude/hooks/audit.py`) logs every Bash command the agent runs to
`.audit.log`, so you can review an unattended session afterward.

## Where it leaks (read this)

This is a **blast-radius reducer for a trusted-but-fallible agent, not a VM** — don't run genuinely untrusted or adversarial code in it. The short version: shared host kernel, read-write host mounts, open network, and pattern-based (so not airtight) permission rules. The article walks through each limit and why it's an acceptable trade for this threat model — read it before you rely on this.

## Production notes

This image is a deliberately minimal baseline: enough to run the agent and a basic build, no more. For real work you add your own toolchain (Miniconda, Node, compilers) on top. Two things are worth knowing when you do:

- **Native wheels and conda want an `exec` `/tmp`.** The hardened config mounts `/tmp` as `noexec`, which blocks `pip` from building native extensions and conda from running post-link scripts. If your stack needs them, drop `noexec` from the `/tmp` line in `.devcontainer/devcontainer.json`; it's a scoped, deliberate loosening. (The article's *"Where my personal in-use image differs"* walks through the trade.)
- **Capabilities only come back with a root entrypoint.** This image starts non-root, so `--cap-drop=ALL` is the whole story. Only if you switch to a root entrypoint (to fix mount ownership, then drop privileges) would you add back a minimal set: `SETUID`, `SETGID`, `CHOWN`, `FOWNER`, `DAC_OVERRIDE`.

## License

MIT — see [LICENSE](LICENSE). Copy it, adapt it, ship it.
