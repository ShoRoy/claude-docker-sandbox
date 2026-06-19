#!/usr/bin/env python3
"""Append every Bash command the agent runs to an audit log.

Wired as a PreToolUse(Bash) hook in .claude/settings.json. Claude Code passes the
tool call as JSON on stdin; we record a timestamped line and exit 0 so the call
proceeds. Pure stdlib, no dependencies. Failures are swallowed so the hook can
never block a tool call.
"""
import datetime
import json
import os
import sys

LOG = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".audit.log")

try:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a") as f:
        f.write(f"{stamp}  {cmd}\n")
except Exception:
    pass  # never let auditing break a tool call

sys.exit(0)
