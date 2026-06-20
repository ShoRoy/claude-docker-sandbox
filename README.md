# claude-docker-sandbox

A small, sensibly-hardened **Docker dev container for running an AI coding agent
(Claude Code) on WSL** — so it can edit your codebase freely but can't touch your
host machine or read the files it has no business reading.

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

- **Windows 10/11 with WSL 2** and an Ubuntu (or other Linux) distro — `wsl --install`, then confirm with `wsl -l -v`.
- **Docker Desktop for Windows** with the **WSL 2 backend** (modern installers default to it; confirm under *Settings → General → "Use WSL 2 based engine"*), and **WSL integration enabled** for your distro (*Settings → Resources → WSL Integration*).
- **VS Code** + the **Dev Containers** extension (`ms-vscode-remote.remote-containers`). The repo auto-installs the **Claude Code** extension inside the container.
- Keep the project on the **WSL filesystem** (`~/...`), not under `/mnt/c` — Windows-mounted paths are slower and cause file-watching and permission quirks.

New to the Windows + WSL + Docker Desktop setup? The full first-time walkthrough is in **[SETUP.md](SETUP.md)**.

> **Two WSL gotchas worth knowing.** (1) Open the project *from WSL* — run `code .` in the WSL shell and check the corner reads `WSL: Ubuntu`; it's the recommended path for speed and correct path handling. (2) With Docker Desktop running, `docker ps` should just work in WSL — you do **not** start `dockerd` manually. (systemd is fine to leave on; if integration misbehaves, update WSL + Docker Desktop first — see SETUP.md.)

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

1. **`.claude/settings.json`** — replace the example paths
   (`/workspace/project/restricted/**`, `params/sensitive_values.conf`) with the
   files in *your* tree that the agent must not read. `deny` beats `allow`, so the
   build still compiles them (a child `gfortran`/`gcc` reads them as you) while the
   agent's own `cat`/`Read` is refused.
2. **`.devcontainer/devcontainer.json`** — adjust the `mounts` to expose only what
   the agent should touch; mark read-only trees with `,readonly`.
3. **`CLAUDE.md`** (create in your project) — the behavioral contract: list the
   restricted paths and ask the agent to treat them as opaque and not route around
   the rules. (Template in the article.)

The audit hook (`.claude/hooks/audit.py`) logs every Bash command the agent runs to
`.audit.log`, so you can review an unattended session afterward.

## Where it leaks (read this)

This is a **blast-radius reducer for a trusted-but-fallible agent, not a VM.** Be
honest about the limits before you rely on it:

- The container **shares the host kernel** — a kernel exploit can cross it. Not for
  genuinely untrusted or adversarial code; use a VM for that.
- The **mounted folders are real host data** (read-write), not throwaway copies.
- The **network is open** — this controls what the agent can touch on your machine,
  not what it can send out. For exfiltration concerns, add `--network none` or an
  egress allowlist.
- The permission rules **match patterns**, so a determined bypass exists (which is
  why the soft-layer contract asks the agent not to look for one).

## Production variant

The minimal image above is the teaching baseline. A scientific-computing build adds
Miniconda, Node, and a compiler/render toolchain, and runs `/tmp` with `exec` (native
wheels and conda post-link scripts execute from scratch). See the article's appendix
for that Dockerfile and `devcontainer.json`. Note: if you start the container as root
with an entrypoint that fixes ownership and drops privileges, that's the one case
where you add back a few capabilities (`SETUID`/`SETGID`/`CHOWN`/`FOWNER`/`DAC_OVERRIDE`);
under the non-root start used here, `--cap-drop=ALL` alone is the whole story.

## License

MIT — see [LICENSE](LICENSE). Copy it, adapt it, ship it.
