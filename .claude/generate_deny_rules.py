#!/usr/bin/env python3
"""
generate_deny_rules.py — build the Layer 2 permission rules for claude-docker-sandbox.

The "restricted files" deny list is large because protecting a path means blocking
every command shape that could read it — not just the Read tool, but cat/less/grep,
the compression and archive tools, every interpreter, and so on. Maintaining that by
hand is error-prone, so it's generated: edit the SOURCE OF TRUTH below (your restricted
paths) and re-run.

  python3 .claude/generate_deny_rules.py            # preview rule count
  python3 .claude/generate_deny_rules.py --write     # (re)write .claude/settings.json

The emitted settings.json is strict JSON (Claude Code does not support comments in
settings files as of 2026), so all the explanation lives here in the script.

The goal: the restricted paths stay COMPILABLE BUT UNREADABLE to the agent. The build
(make/cmake/...) is allowed and reads them as a child process; the agent's own
Read/cat/grep/... is denied. "deny" beats "allow".

This is pattern-based, so it is NOT airtight (see the article's "Where it leaks"): it
catches the command shapes below. The container (Layer 1) and CLAUDE.md (Layer 3) cover
what patterns can't — e.g. `python3 -c "open('/restricted/x').read()"`, where the path
hides inside a quoted string the matcher never parses.
"""
import argparse
import json
import os
import sys

# ============================================================================
# SOURCE OF TRUTH — edit these for your project, then re-run with --write
# ============================================================================

# Folders whose every descendant must be opaque to the agent.
RESTRICTED_FOLDERS = [
    "/workspace/project/restricted",
]
# Individual files to keep opaque.
RESTRICTED_FILES = [
    "/workspace/project/params/sensitive_values.conf",
]

# Commands that prompt me (irreversible / outbound), and commands that run unattended.
ASK_RULES   = ["Bash(rm *)", "Bash(curl *)", "Bash(wget *)", "Bash(git push *)"]
ALLOW_RULES = ["Bash(make *)", "Bash(cmake *)", "Bash(mpiexec *)"]

# The audit hook (logs every Bash command the agent runs).
HOOK_COMMAND = "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/audit.py"

# Belt-and-suspenders: emit 3 glob spellings per folder instead of just /**.
# Off by default for a readable file; on if your matcher needs the redundancy.
MULTI_GLOB = False

# --- Tool-level commands (Claude Code's own tools) --------------------------
TOOL_COMMANDS = ["Read", "Edit", "Write", "NotebookEdit", "Grep", "Glob"]

# --- Bash commands that could read a file's contents or move them out --------
# Build tools (make, cmake, ninja, gfortran, gcc, mpif90, ...) are intentionally
# NOT here: the build reads these paths transitively, and that's allowed.
BASH_COMMANDS = [
    # readers / pagers / viewers / editors (open-to-read)
    "cat", "head", "tail", "tac", "less", "more", "most", "bat", "nl",
    "view", "vim", "vi", "nvim", "nano", "emacs", "code", "gedit", "pico",
    "xxd", "od", "hexdump", "strings",
    # filters that take a file argument
    "awk", "gawk", "mawk", "nawk", "sed", "grep", "egrep", "fgrep", "rg",
    "cut", "wc", "sort", "uniq", "diff", "cmp", "comm", "join", "paste",
    "tr", "expand", "unexpand", "column", "rev",
    # metadata / listing / search
    "ls", "ll", "find", "tree", "stat", "file", "du", "readlink", "realpath",
    # checksums (fingerprint the contents)
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "cksum", "b2sum", "crc32",
    # encoders (emit a restricted file's bytes to stdout or a file = read-exfil)
    "base64", "base32", "basenc", "uuencode",
    # archive / copy / move / exfil
    "tar", "zip", "unzip", "cpio", "pax", "dd", "cp", "mv", "install",
    "rsync", "scp", "sftp",
    "bsdtar", "gtar", "star", "bsdcpio", "ar",    # tar/cpio variants + ar
    # compression (read content into a compressed stream)
    "gzip", "gunzip", "zcat", "bzip2", "bunzip2", "bzcat",
    "xz", "unxz", "xzcat", "lzma", "zstd", "zstdcat", "7z", "7za",
    "lz4", "lzop", "pigz", "pbzip2",
    # symlink / hardlink (re-expose under a non-denied name)
    "ln",
    # writers / mutators
    "touch", "mkdir", "rm", "rmdir", "tee", "truncate",
    "chmod", "chown", "chgrp", "setfacl",
    # structured-data readers
    "jq", "yq", "xmllint", "xmlstarlet", "json_pp",
    # language interpreters (read via a one-liner or script)
    "python", "python3", "python2", "perl", "perl5", "ruby",
    "node", "nodejs", "lua", "tclsh", "Rscript", "R", "php", "julia", "expect",
    # version control
    "git", "hg", "svn", "bzr",
    # shells (run a restricted file as a script, or -c a reader)
    "sh", "bash", "zsh", "dash", "ksh", "fish",
]

# Readers-only subset, applied to single-FILE targets. A lone file can't be the
# target of dir/create commands (mkdir, rmdir, tree, ...), so those would be
# dead rules — this drops them and keeps only commands that can read/move/expose
# the file's contents.
BASH_COMMANDS_FILE = [
    # readers / pagers / viewers / editors (open-to-read)
    "cat", "head", "tail", "tac", "less", "more", "most", "bat", "nl",
    "view", "vim", "vi", "nvim", "nano", "emacs", "code", "gedit", "pico",
    "xxd", "od", "hexdump", "strings",
    # filters that take a file argument
    "awk", "gawk", "mawk", "nawk", "sed", "grep", "egrep", "fgrep", "rg",
    "cut", "wc", "sort", "uniq", "diff", "cmp", "comm", "join", "paste",
    "tr", "expand", "unexpand", "column", "rev",
    # metadata / checksum
    "stat", "file", "readlink", "realpath",
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "cksum", "b2sum", "crc32",
    # encoders (emit a restricted file's bytes to stdout or a file = read-exfil)
    "base64", "base32", "basenc", "uuencode",
    # archive / copy / move / exfil (read the file out)
    "tar", "zip", "cpio", "pax", "dd", "cp", "mv", "install", "rsync", "scp", "sftp",
    "bsdtar", "gtar", "star", "bsdcpio", "ar",
    # compression (read content into a stream)
    "gzip", "bzip2", "xz", "lzma", "zstd", "7z", "7za", "zcat", "bzcat", "xzcat", "zstdcat",
    "lz4", "lzop", "pigz", "pbzip2",
    # symlink / write-through
    "ln", "tee",
    # structured-data readers
    "jq", "yq", "xmllint", "xmlstarlet", "json_pp",
    # language interpreters (read via a one-liner or script)
    "python", "python3", "python2", "perl", "perl5", "ruby",
    "node", "nodejs", "lua", "tclsh", "Rscript", "R", "php", "julia", "expect",
    # version control
    "git", "hg", "svn", "bzr",
    # shells
    "sh", "bash", "zsh", "dash", "ksh", "fish",
]


# ============================================================================
# generation
# ============================================================================
def folder_targets(path):
    if MULTI_GLOB:
        return [f"{path}/*", f"{path}/**", f"{path}/**/*"]
    return [f"{path}/**"]


def deny_rules():
    rules = []
    # (target, bash-command-set) pairs: folders get the full list, single files
    # get the readers-only subset (no dir/create commands on a lone file).
    targets = []
    for f in RESTRICTED_FOLDERS:
        for g in folder_targets(f):
            targets.append((g, BASH_COMMANDS))
    for f in RESTRICTED_FILES:
        targets.append((f, BASH_COMMANDS_FILE))
    for t, cmds in targets:
        for tool in TOOL_COMMANDS:
            rules.append(f"{tool}({t})")
        for cmd in cmds:
            rules.append(f"Bash({cmd} {t})")      # bare:  cmd /path
            rules.append(f"Bash({cmd} * {t})")    # flagged: cmd -x /path
    # de-dup while preserving order
    seen, out = set(), []
    for r in rules:
        if r not in seen:
            seen.add(r); out.append(r)
    return out


def build_settings():
    return {
        "permissions": {
            "defaultMode": "default",
            "disableBypassPermissionsMode": "disable",
            "deny": deny_rules(),
            "ask": ASK_RULES,
            "allow": ALLOW_RULES,
        },
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "command": HOOK_COMMAND}],
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Generate Layer-2 deny rules for settings.json")
    ap.add_argument("--write", action="store_true", help="write .claude/settings.json (default: preview)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json"))
    args = ap.parse_args()

    settings = build_settings()
    deny = settings["permissions"]["deny"]
    print(f"[summary] {len(RESTRICTED_FOLDERS)} folder(s) + {len(RESTRICTED_FILES)} file(s)")
    print(f"          {len(TOOL_COMMANDS)} tool-level + {len(BASH_COMMANDS)} Bash (folders) / "
          f"{len(BASH_COMMANDS_FILE)} Bash (files), x2 forms{'  x3 globs' if MULTI_GLOB else ''}")
    print(f"          -> {len(deny)} deny rules")
    if not args.write:
        print("DRY-RUN. Re-run with --write to (over)write settings.json.")
        return 0
    # Claude Code's settings.json must be STRICT JSON (no comments supported as of
    # 2026), so this file is generated without them — the documentation lives in
    # this script and in the README, not in the emitted file.
    body = json.dumps(settings, indent=2) + "\n"
    with open(args.out, "w") as fh:
        fh.write(body)
    print(f"[written] {args.out}  ({len(body)} bytes, strict JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
