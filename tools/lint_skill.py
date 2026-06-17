#!/usr/bin/env python3
"""Generic Agent Skill (SKILL.md) format linter.

Validates one or more skill directories against the Claude Code / Agent Skills
SKILL.md format and exits non-zero on any error. For each violation it prints
*where* it is and *how to fix it*, so a human or an AI agent can self-correct.

This is itself an audit in the spirit of this repository: it enumerates the full
set of skills (not a sample), is deterministic, exits non-zero on violation, and
reports actionable messages.

Usage:
    python tools/lint_skill.py [SKILL_DIR ...]

With no arguments it recursively discovers every ``SKILL.md`` under the current
directory (skipping VCS/vendor dirs) and validates each skill, so it keeps
working as more skills are added later, including samples under ``examples/``.

Constraints enforced follow the Claude Code Skills docs and the Agent Skills
specification (name/description limits, enum/boolean field types, directory-name
match, SKILL.md location). Recommendations (unknown fields, body length, the
description + when_to_use display budget) are emitted as warnings, not errors.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.exit("PyYAML is required to run this linter: pip install pyyaml")

# name: 1-64 chars, lowercase alnum + single hyphens, no leading/trailing/double hyphen
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Fields recognized by Agent Skills spec and/or Claude Code. Anything else -> warn.
KNOWN_FIELDS = {
    # required
    "name", "description",
    # Agent Skills spec (optional)
    "license", "compatibility", "metadata", "allowed-tools",
    # Claude Code extensions (optional)
    "when_to_use", "disable-model-invocation", "user-invocable", "argument-hint",
    "arguments", "disallowed-tools", "model", "effort", "context", "agent",
    "hooks", "paths", "shell",
}
EFFORT_VALUES = {"low", "medium", "high", "xhigh", "max"}
SHELL_VALUES = {"bash", "powershell"}

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


class Report:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str, str]] = []
        self.warnings: list[tuple[str, str, str]] = []

    def error(self, where: str, msg: str, fix: str) -> None:
        self.errors.append((where, msg, fix))

    def warn(self, where: str, msg: str, fix: str) -> None:
        self.warnings.append((where, msg, fix))


def split_frontmatter(text: str) -> tuple[str | None, str | None]:
    """Return (frontmatter_text, body) or (None, None) if no valid block."""
    if not text.startswith("---"):
        return None, None
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not m:
        return None, None
    return m.group(1), text[m.end():]


def lint_skill(skill_dir: Path, rep: Report) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        wrong_case = [p for p in skill_dir.glob("*.md") if p.name.lower() == "skill.md"]
        if wrong_case:
            rep.error(str(wrong_case[0]), f"file is {wrong_case[0].name!r}, must be exactly 'SKILL.md'",
                      "rename it to SKILL.md (case-sensitive)")
        else:
            rep.error(str(skill_dir), "no SKILL.md at the skill root",
                      "create <skill-dir>/SKILL.md")
        return

    floc = str(skill_md)
    text = skill_md.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        rep.error(floc, "missing or malformed YAML frontmatter",
                  "wrap the metadata in a block delimited by --- lines at the very top")
        return
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        rep.error(floc, f"frontmatter is not valid YAML: {exc}",
                  "fix the YAML syntax between the --- fences")
        return
    if not isinstance(fm, dict):
        rep.error(floc, "frontmatter must be a YAML mapping", "use key: value pairs")
        return

    name = fm.get("name")
    desc = fm.get("description")

    # --- required presence ---
    if name is None:
        rep.error(floc, "required field 'name' is missing", "add `name: <skill-dir-name>`")
    if desc is None:
        rep.error(floc, "required field 'description' is missing", "add a `description:` field")

    # --- name ---
    if isinstance(name, str):
        if not 1 <= len(name) <= 64:
            rep.error(floc, f"'name' length {len(name)} is out of range 1-64",
                      "use a name between 1 and 64 characters")
        if not NAME_RE.match(name):
            rep.error(floc, f"'name' = {name!r} violates ^[a-z0-9]+(-[a-z0-9]+)*$",
                      "lowercase letters/digits and single hyphens only; no leading, trailing or double hyphen")
        elif name != skill_dir.name:
            rep.error(floc, f"'name' ({name!r}) must match the directory name ({skill_dir.name!r})",
                      "rename the directory or the name field so they match")
    elif name is not None:
        rep.error(floc, "'name' must be a string", "quote the value as a string")

    # --- description ---
    if isinstance(desc, str):
        n = len(desc)
        if n < 1:
            rep.error(floc, "'description' is empty", "write a non-empty description")
        elif n > 1024:
            rep.error(floc, f"'description' is {n} chars, over the 1024 limit (by {n - 1024})",
                      "shorten the description to at most 1024 characters")
    elif desc is not None:
        rep.error(floc, "'description' must be a string", "quote the value as a string")

    # --- enum fields ---
    eff = fm.get("effort")
    if eff is not None and eff not in EFFORT_VALUES:
        rep.error(floc, f"'effort' = {eff!r} is not one of {sorted(EFFORT_VALUES)}",
                  "use a valid effort value or remove the field")
    shell = fm.get("shell")
    if shell is not None and shell not in SHELL_VALUES:
        rep.error(floc, f"'shell' = {shell!r} is not one of {sorted(SHELL_VALUES)}",
                  "use 'bash' or 'powershell'")
    ctx = fm.get("context")
    if ctx is not None and ctx != "fork":
        rep.error(floc, f"'context' = {ctx!r}; only 'fork' is allowed",
                  "set `context: fork` or remove the field")

    # --- boolean fields ---
    for bf in ("disable-model-invocation", "user-invocable"):
        if bf in fm and not isinstance(fm[bf], bool):
            rep.error(floc, f"'{bf}' must be a boolean, got {type(fm[bf]).__name__}",
                      f"set `{bf}: true` or `{bf}: false` (unquoted)")

    # --- compatibility length ---
    comp = fm.get("compatibility")
    if isinstance(comp, str) and not 1 <= len(comp) <= 500:
        rep.error(floc, f"'compatibility' length {len(comp)} is out of range 1-500",
                  "trim compatibility to at most 500 characters")

    # --- warnings ---
    wtu = fm.get("when_to_use")
    if isinstance(desc, str) and isinstance(wtu, str) and len(desc) + len(wtu) > 1536:
        rep.warn(floc, f"description + when_to_use = {len(desc) + len(wtu)} chars (>1536)",
                 "the skill listing truncates the combined text; shorten one of them")

    for key in fm:
        if key not in KNOWN_FIELDS:
            rep.warn(floc, f"unknown frontmatter field {key!r}",
                     "remove it or check the spelling against the skill spec")

    if body is not None:
        nlines = body.count("\n") + 1
        if nlines > 500:
            rep.warn(floc, f"SKILL.md body is {nlines} lines (>500 recommended)",
                     "move detail into references/ files (progressive disclosure)")

    # --- Docs audit: relative links in the body must resolve ---
    if body is not None:
        for raw in MD_LINK_RE.findall(body):
            link = raw.strip()
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path_part = link.split("#", 1)[0].split(" ", 1)[0]
            if not path_part:
                continue
            if not (skill_dir / path_part).exists():
                rep.error(floc, f"relative link target does not exist: {link}",
                          "fix the path or restore the missing file")


def discover(args: list[str]) -> list[Path]:
    if args:
        return [Path(a) for a in args]
    # Recurse so skills nested under examples/ (or any future subtree) are found,
    # but skip VCS/vendor/build dirs that may carry unrelated files.
    skip = {".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", "dist", "build"}
    found = {
        p.parent
        for p in Path(".").rglob("SKILL.md")
        if not any(part in skip for part in p.parts)
    }
    return sorted(found)


def main(argv: list[str]) -> int:
    skills = discover(argv)
    if not skills:
        print("no skills found (looked for SKILL.md recursively); pass a skill directory explicitly.")
        return 1

    rep = Report()
    for skill in skills:
        lint_skill(skill, rep)

    for where, msg, fix in rep.warnings:
        print(f"⚠ {where}: {msg}\n    → {fix}")
    for where, msg, fix in rep.errors:
        print(f"✗ {where}: {msg}\n    → {fix}")

    count = len(skills)
    if rep.errors:
        print(f"\nFAIL: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s) "
              f"across {count} skill(s)")
        return 1
    print(f"\nOK: {count} skill(s) valid, {len(rep.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
