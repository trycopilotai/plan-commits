#!/usr/bin/env python3
"""Render an agent invocation's raw JSON-lines output as text.

    python3 scripts/render_invocation.py --client claude-code \
        --prompt prompt.txt --root <fixture> --plugin-root <clone> \
        --home <home> --hostname <name> raw.jsonl > transcript.txt

Add --isolation-root <dir> for a run made in a fresh temporary
directory that holds both the fixture and the plugin directory.
Add --calls-out <file> to also write every tool call's name and
full, uncut arguments as JSON, with the same replacements, so a
check can read what the transcript cuts.

What it writes, and every way it departs from the raw output:

- a header: the client, and for Claude Code the version and
  model from the init event;
- the prompt file, with trailing newlines removed;
- the tool calls, numbered. Claude Code: each tool_use's
  name and input, and a status of ok or error from the
  matching tool_result, or unknown if there is none. Codex:
  each completed command_execution's command, status and
  exit code; each other completed item, except reasoning
  items and agent messages, written whole;
- the final message: Claude Code's result event, or Codex's
  last agent message; "(none)" if there is neither. Earlier
  Codex agent messages and all reasoning are left out;
- arguments re-serialised as JSON with sorted keys, and each
  string in them longer than LIMIT characters cut there and
  marked ...[N more characters] (not in --calls-out);
- no tool output, and no event of any other kind.

Then, over the whole text, these replacements, in this
order, each applied to a whole path prefix and never inside
a longer name: each --isolation-root (also in its form
without a leading /private) becomes /iso, each --plugin-root
(the directory the client loaded the skill from) /plugin,
the fixture's absolute path /work, a client scratch
directory /private/tmp/claude-<uid>/<slug> /scratch, the
home directory ~, and each --hostname host.
Standard library only; output depends only on the inputs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

LIMIT = 300
# A path or name ends at a separator, a quote, whitespace or the end.
END = r"(?=[/\\\s\"'`]|$)"
SCRATCH = re.compile(r"/private/tmp/claude-[0-9]+/[^/\s\"'`]+" + END)


def prefix(text: str, path: str, replacement: str) -> str:
    """Replace `path` where it is a whole path prefix."""
    pattern = r"(?<![\w.-])" + re.escape(path.rstrip("/")) + END
    return re.sub(pattern, lambda match: replacement, text)


def isolated(path: str, roots: list) -> str:
    """`path` as it reads after the isolation roots became /iso."""
    for root in roots:
        if path == root or path.startswith(root.rstrip("/") + "/"):
            return "/iso" + path[len(root.rstrip("/")):]
    return path


def cut(value):
    if isinstance(value, str):
        if len(value) > LIMIT:
            return value[:LIMIT] + "...[%d more characters]" % (len(value) - LIMIT)
        return value
    if isinstance(value, dict):
        return {key: cut(item) for key, item in value.items()}
    if isinstance(value, list):
        return [cut(item) for item in value]
    return value


def arguments(value) -> str:
    return json.dumps(cut(value), ensure_ascii=False, sort_keys=True)


def claude_code(events):
    calls, final, model, version = [], None, None, None
    results = {}
    for event in events:
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            model, version = event.get("model"), event.get("claude_code_version")
        elif kind in ("assistant", "user"):
            content = event["message"].get("content")
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_use":
                    calls.append((block["id"], block["name"], block.get("input")))
                elif block.get("type") == "tool_result":
                    results[block["tool_use_id"]] = (
                        "error" if block.get("is_error") else "ok"
                    )
        elif kind == "result":
            final = event.get("result")
    header = ["client: Claude Code %s" % version, "model: %s" % model]
    lines = [
        "%s %s\n  status: %s" % (name, arguments(given), results.get(ident, "unknown"))
        for ident, name, given in calls
    ]
    full = [{"name": name, "arguments": given} for _ident, name, given in calls]
    return header, lines, final, full


def codex(events):
    lines, final, full = [], None, []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event["item"]
        if item.get("type") == "command_execution":
            lines.append(
                "command_execution %s\n  status: %s, exit %s"
                % (arguments({"command": item["command"]}), item.get("status"), item.get("exit_code"))
            )
            full.append({"name": "command_execution", "arguments": {"command": item["command"]}})
        elif item.get("type") == "agent_message":
            final = item["text"]
        elif item.get("type") not in ("reasoning",):
            lines.append("%s %s" % (item.get("type"), arguments(item)))
            full.append({"name": item.get("type"), "arguments": item})
    return ["client: Codex"], lines, final, full


def replace(text: str, options) -> str:
    """Apply the declared replacements, in order."""
    for path in options.isolation_root:
        forms = [path]
        if path.startswith("/private/"):
            forms.append(path[len("/private"):])
        for form in forms:
            text = prefix(text, form, "/iso")
    for path in options.plugin_root:
        path = isolated(path, options.isolation_root)
        text = prefix(text, path, "/plugin")
    text = prefix(text, isolated(options.root, options.isolation_root), "/work")
    text = SCRATCH.sub(lambda match: "/scratch", text)
    text = prefix(text, options.home, "~")
    for name in sorted(options.hostname, key=len, reverse=True):
        text = re.sub(
            r"(?<![\w.-])" + re.escape(name) + r"(?![\w-]|\.\w)",
            lambda match: "host",
            text,
        )
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=("claude-code", "codex"), required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--isolation-root", action="append", default=[])
    parser.add_argument("--plugin-root", action="append", default=[])
    parser.add_argument("--home", required=True)
    parser.add_argument("--hostname", action="append", default=[])
    parser.add_argument("--calls-out")
    parser.add_argument("raw")
    options = parser.parse_args(argv)
    with open(options.raw, encoding="utf-8") as stream:
        events = [json.loads(line) for line in stream if line.strip()]
    with open(options.prompt, encoding="utf-8") as stream:
        prompt = stream.read().rstrip("\n")
    render = claude_code if options.client == "claude-code" else codex
    header, lines, final, full = render(events)
    text = "\n".join(
        header
        + ["", "## prompt", "", prompt, "", "## tool calls", ""]
        + ["%d. %s" % (number, line) for number, line in enumerate(lines, 1)]
        + ["", "## final message", "", final if final is not None else "(none)", ""]
    )
    sys.stdout.write(replace(text, options))
    if options.calls_out:
        calls = json.dumps(full, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        with open(options.calls_out, "w", encoding="utf-8") as stream:
            stream.write(replace(calls, options))
    return 0


if __name__ == "__main__":
    sys.exit(main())
