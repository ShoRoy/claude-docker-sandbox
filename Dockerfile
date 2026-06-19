# claude-docker-sandbox — minimal baseline image
# A small, non-root Linux box for running an AI coding agent (Claude Code) under
# Docker Dev Containers on WSL. Hardening lives in .devcontainer/devcontainer.json.
#
# This is the MINIMAL teaching baseline. For the scientific-toolchain version
# (Miniconda, Node, build tools) see README.md → "Production variant".
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Non-root user. UID 1000 lines up with the typical first host user, which keeps
# bind-mounted file ownership sane.
RUN useradd -ms /bin/bash -u 1000 claudeuser \
 && mkdir -p /workspace \
 && chown -R claudeuser:claudeuser /workspace

USER claudeuser
WORKDIR /workspace
