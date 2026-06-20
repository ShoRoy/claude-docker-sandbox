# First-time setup: Windows + WSL + Docker Desktop

This is the host-side walkthrough for getting **claude-docker-sandbox** running from
scratch on Windows. The repo already contains the container itself — the `Dockerfile`,
`.devcontainer/devcontainer.json`, the permission rules in `.claude/`, and the audit
hook — so this guide is about preparing your machine and opening the box, not building
the config by hand.

If you already run Docker Desktop + WSL + VS Code, skip to the [README quickstart](README.md#quickstart).

> For *why* the box is built the way it is — the threat model, the three rule layers,
> and where it leaks — see the article linked from the [README](README.md).

---

## Architecture at a glance

```
Windows
├── Docker Desktop        → manages the Docker daemon
├── VS Code               → editor; attaches to the container
│   ├── Dev Containers extension
│   └── Claude Code extension   (auto-installed inside the container)
└── WSL 2 (Ubuntu)        → the Linux host the container runs on
    └── ~/claude-docker-sandbox   (this repo, cloned here)
        ├── Dockerfile
        ├── .devcontainer/devcontainer.json
        ├── .claude/                (settings.json + hooks/audit.py)
        ├── workspace/              ← your project (you create this)
        └── config/                 ← the container's home (you create this)
```

The division of labor: **Docker Desktop** runs the daemon, **WSL** is the Linux host,
the **dev container** is the isolated execution environment, **VS Code** is the editor
that attaches to it, and the **Claude Code extension** is how you talk to the agent.

---

## Prerequisites

- **Windows 10 or 11.**
- **WSL 2** with a Linux distro (Ubuntu is fine). Install with `wsl --install`, then
  confirm the distro is in version 2:

  ```powershell
  wsl -l -v        # VERSION column should read 2
  ```
- **Docker Desktop for Windows** (installed below).
- **VS Code** (Windows) with the **Dev Containers** extension.

---

## Step 1 — Docker Desktop with the WSL 2 backend

1. Install **Docker Desktop for Windows**. Modern installers select the WSL 2 backend
   by default; you can confirm it under **Settings → General → "Use WSL 2 based engine."**
2. Enable WSL integration: **Settings → Resources → WSL Integration**. Your default
   distro is enabled automatically; tick any others you use. Click **Apply & Restart**.

   > If WSL Integration isn't listed, Docker Desktop may be in Windows-container mode —
   > switch to Linux containers first.

3. Start Docker Desktop.

**Sign-in is optional by default** for local builds, WSL integration, and Dev Containers.
You only need an account for Docker Hub pull-rate-limit relief or paid features — though
some organizations enforce sign-in via policy.

> **Licensing:** Docker Desktop is free for personal use, education, non-commercial open
> source, and small businesses (**< 250 employees *and* < $10M annual revenue**). Larger
> organizations (≥ 250 employees *or* ≥ $10M revenue) and government entities need a paid
> subscription.

---

## Step 2 — Verify Docker from WSL

With **Docker Desktop running**, open your WSL shell and run:

```bash
docker ps
```

```
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
```

An empty list is correct. This confirms Docker Desktop is running and WSL integration
works. Docker Desktop manages the daemon, so **you do not start `dockerd` manually** —
if an old setup added `sudo dockerd` (or `sudo service docker start`) to your `~/.bashrc`,
remove it; there's no separate daemon to launch in WSL.

> **If `docker ps` fails or integration misbehaves** (startup error dialogs, or `docker
> login` succeeds but you can't pull/push): update both first — `wsl --update`, update
> Docker Desktop, then `wsl --shutdown` and reopen. That resolves the large majority of
> integration/proxy errors. If login still fails, it's a credential-helper issue, not a
> systemd one: edit `~/.docker/config.json` in your WSL distro and remove the
> `"credsStore": "desktop.exe"` line, then retry `docker login`.
>
> **systemd is fine to leave on.** It's the default init for current Ubuntu on WSL and
> is supported — you do *not* need to disable it for Docker Desktop. (Old tutorials
> suggesting `systemd=false` in `/etc/wsl.conf` trace to a 2022 bug and are no longer
> recommended; it can break other systemd-dependent tools. Last resort only.)

---

## Step 3 — VS Code extensions

In VS Code (Windows), install:

1. **Dev Containers** — `ms-vscode-remote.remote-containers` (the marketplace ID keeps
   the legacy `remote-containers` slug; that's expected).
2. **WSL** — `ms-vscode-remote.remote-wsl` (so VS Code can attach to your WSL distro).

The **Claude Code** extension is installed automatically *inside* the container by this
repo's `devcontainer.json`, so you don't need it on the Windows side.

---

## Step 4 — Clone the repo into your WSL home

From the **WSL shell** (not PowerShell), clone into the WSL filesystem — not under
`/mnt/c`. Code under `/mnt/c` crosses the Windows↔WSL boundary, which makes bind-mount
I/O noticeably slower and can break file-watching and cause permission/line-ending
mismatches.

```bash
cd ~
git clone https://github.com/ShoRoy/claude-docker-sandbox.git
cd claude-docker-sandbox

# create the two bind-mount targets the container expects
mkdir -p workspace config
```

Put (or symlink) the project you want the agent to work on under `workspace/`. Quick
sanity check of the layout:

```bash
ls -A
# .claude  .devcontainer  .gitignore  CHANGELOG.md  config  Dockerfile  LICENSE  README.md  SETUP.md  workspace
```

Before you open it, edit `.claude/settings.json` — swap the example restricted paths
(`/workspace/project/restricted/**`, `params/sensitive_values.conf`) for the files in
*your* tree the agent must not read. (See the README's "Edit these for your project.")

---

## Step 5 — Open the project from WSL

From the WSL shell, in the repo directory:

```bash
code .
```

Check the bottom-left corner of VS Code — it should read **`WSL: Ubuntu`** (your distro).
Opening from WSL this way is recommended: the container builds against the WSL-filesystem
copy of your code, which gives good performance and correct path handling.

---

## Step 6 — Reopen in the container

Open the Command Palette (**F1** or **Ctrl+Shift+P**) and run:

```
Dev Containers: Reopen in Container
```

VS Code builds the image from the repo's `Dockerfile` and attaches. The first build
takes a couple of minutes; later opens are fast. (Use **Dev Containers: Rebuild and
Reopen in Container** only after you change the `Dockerfile` or `devcontainer.json`.)

Expected terminal prompt inside the container:

```bash
claudeuser@<container-id>:/workspace$
```

---

## Step 7 — Verify the box

In the container's integrated terminal:

```bash
whoami      # -> claudeuser   (non-root)
pwd         # -> /workspace
```

Confirm the bind mount works both ways — a file written inside the container appears on
the WSL host:

```bash
touch /workspace/_it_works.txt
# on the WSL host it's at ~/claude-docker-sandbox/workspace/_it_works.txt
```

> **What persists:** `config/` is mounted as the container's home (`/home/claudeuser`),
> so shell history, the VS Code server, and user-level config survive across rebuilds.
> `workspace/` is your project. Everything else in the container is disposable.

---

## Using Claude in the box

Talk to the agent through the **Claude Code extension** (auto-installed in the container),
signed in with your Claude account. You do **not** need an API key or the Claude CLI for
this workflow — and there's a small reason not to add them casually: a static
`ANTHROPIC_API_KEY` is a long-lived secret, and the CLI authenticates separately from the
extension. Add either only if you specifically want CLI-based or API-based usage.

---

## The daily loop

1. Start Docker Desktop (if it isn't running).
2. In the WSL shell: `cd ~/claude-docker-sandbox && code .`
3. **Dev Containers: Reopen in Container.**
4. Work. Your files persist under `workspace/`; the audit log (`.audit.log`) records every
   command the agent ran.
5. Close VS Code when done; stop Docker Desktop from the Windows tray if you don't want it
   resident.

---

## Sanity checklist

The setup is correct when:

- [ ] `docker ps` works in WSL with Docker Desktop running (no manual `dockerd`).
- [ ] The repo lives under your WSL home (`~/claude-docker-sandbox`), not `/mnt/c`.
- [ ] `workspace/` and `config/` exist alongside the repo's files.
- [ ] VS Code opened from WSL shows `WSL: Ubuntu`.
- [ ] **Dev Containers: Reopen in Container** builds and attaches.
- [ ] Inside the container, `whoami` → `claudeuser` and `pwd` → `/workspace`.
- [ ] You're using the Claude Code extension, not an API key.

---

## Next

- **Why it's built this way** (threat model, the three layers, where it leaks): the article
  linked from the [README](README.md).
- **A heavier scientific-computing image** (Miniconda, Node, compilers; `exec` scratch):
  see the README's [Production variant](README.md#production-variant).
- **Tightening the permission rules** for your own restricted files: the README's
  "Edit these for your project," and the article for the full tiered-deny reasoning.
