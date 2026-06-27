---
name: knowledge-audit
description: >-
  Audits AI knowledge across a 5-layer architecture and reconciles it to its
  desired state — promoting, demoting, and pruning knowledge so that each piece
  lives in the right layer, has no duplicates (SSoT), and carries a Why. Use
  this skill when the user asks to: organize/promote/demote knowledge layers,
  audit CLAUDE.md or AGENTS.md for misplaced content, extract globally
  applicable rules from project memory, create or update knowledge/ files, or
  run a periodic knowledge consolidation. Also invoke proactively after a memory
  consolidation session if universally applicable rules appear in project memory.
  Complements audit-driven-feedback (which audits code/config integrity); this
  audits the AI knowledge fed into the system.
---

# Knowledge Audit

Scans project documents and reconciles knowledge to its correct layer in the
5-layer architecture — promoting, demoting, and removing stale entries until
each piece of knowledge lives where it belongs.

## 5-Layer Architecture

| Priority | Location | Role | When loaded |
|---|---|---|---|
| 1 | `~/.claude/CLAUDE.md` | Policy — principles, rules, promotion criteria | Auto-loaded every session |
| 2 | `~/.claude/knowledge/*.md` | Tool Knowledge — Fact / Rules / Why | Manual load on trigger |
| 3 | `~/.claude/commands/*.md` | Skills — procedures, checklists, CLI steps | Loaded on invocation |
| 4 | `projects/<name>/memory/` | Project Memory — project-specific decisions | Auto-loaded in project |
| 5 | `AGENTS.md` / project `CLAUDE.md` | AI-shared rules | All AI tools (Gemini, Copilot, etc.) |

**Layer roles in one line each**:
- Policy = *what* to protect (principles, prohibitions, decision criteria)
- Knowledge = *why* to do it (Fact/Rules/Why format, loaded on demand)
- Skill = *how* to do it (procedures, checklists, command sequences)

## Step 1: Confirm Scan Targets

If the user has not specified, default to:

- `AGENTS.md` or project `CLAUDE.md` (project root)
- `.claude/commands/` (skill files)
- `docs/` (design docs, ADRs)
- `projects/<name>/memory/MEMORY.md` (project memory index)
- `~/.claude/CLAUDE.md` (as a demotion / Policy Audit target)

Use the Explore agent for efficient scanning.

## Step 2: Build the Candidate Inventory

Read each document and look for signals in the following categories:

**Knowledge promotion signals (→ `~/.claude/knowledge/`)**

| Category | Example signals |
|---|---|
| Failure patterns | "doing X causes bug", "avoid this implementation" |
| Performance pitfalls | "no API call per tick", "N+1 query trap" |
| Safety rules | "`# type: ignore` forbidden", "SQL injection prevention" |
| Operations rules | "keep DEBUG logs", "include type + message in exception logs" |
| Design principles | "SRP: back-reference count is the primary metric" |
| Tool quirks | "git worktree path misuse", "mypy stub limitations" |
| Review criteria | "no sync IO inside async", "falsy vs None" |
| Audit criteria | "fat-class detection threshold", "back-reference measurement" |

**Policy promotion signals (→ `~/.claude/CLAUDE.md`)**
- Principles that answer "what to protect" and decision criteria

**Skill signals (→ `~/.claude/commands/`)**
- Multi-step procedures, checklists, CLI command sequences

**Demotion signals (→ project memory or AGENTS.md)**
- Content in `~/.claude/CLAUDE.md` that is project-specific
- Descriptions qualified with "in this project, we do X"

### Candidate Inventory (always produce this at the end of Step 2)

After scanning, compile this table before proceeding to promotion checks:

| Candidate | Category | Current layer | Proposed layer | Reason (1 line) | Confidence |
|---|---|---|---|---|---|
| Rule X | Failure pattern | AGENTS.md | knowledge/ | Valid across projects | High |
| Procedure Y | — | Policy | Skill | It is a "how", not a "what" | High |
| Setting Z | Tool quirk | Project Memory | knowledge/ | Recurs across projects | Medium |

Candidates with Medium or lower confidence require careful evaluation in Step 3.

## Step 3: Promotion Gate (all items must be Yes)

For each candidate:

- [ ] **Valid in 2+ projects** (not project-specific)
- [ ] **Likely valid for 6+ months** (unlikely to be invalidated by tool version bumps)
- [ ] **Does not depend on project-specific context**
- [ ] **Should NOT be a Skill** (i.e., it is knowledge, not a procedure)
- [ ] **Why can be articulated**

If any item is No, do not promote (leave in project memory or AGENTS.md).

## Step 4: Create the Knowledge File

Once promotion is confirmed, create `~/.claude/knowledge/<slug>.md`.

### Front matter

```yaml
---
id: <kebab-case-slug>
tags: [python, design, ...]       # search tags
category: tool | design | language | operations | security
review: YYYY-MM                   # next review date (~3 months out)
priority: high | medium | low
---
```

### Body — Fact / Rules / Why format

```markdown
# <Title>

**Fact**
<Why this rule was needed — concrete symptom or incident, briefly>

**Rules**
1. **<Rule name>** — <content>

Code blocks showing NG / OK examples are effective here.

**Why**
- Rule 1: <why this rule>
- Rule 2: <why this rule>
```

## Step 5: Update the Trigger Table in CLAUDE.md

Add a new row to the "Tool Knowledge" trigger table in `~/.claude/CLAUDE.md`:

```markdown
| <Trigger condition (when to load)> | `knowledge/<slug>.md` | <One-line summary> |
```

Write the trigger condition as "when doing X" so readers know exactly when to load it.

## Step 6: Policy Audit and Demotion

### Policy Audit — check for "How" contamination in CLAUDE.md

Flag these as **Skill candidates** if found in Policy (CLAUDE.md):

- Lists of CLI commands (`git commit -m ...`, specific operation steps)
- Checklist-style procedures ("Step 1 → Step 2 → ...")
- Detailed tool usage (command options, flags)

Policy should only answer "what to protect and why"; "how to do it" belongs in the Skill layer.

### Demotion — moving project-specific content to project memory

If `~/.claude/CLAUDE.md` contains project-specific content:

1. Move it to the appropriate project memory file
2. Remove it from `~/.claude/CLAUDE.md`
3. Update the `MEMORY.md` index

## Important: SSoT Exception Rule

**Do NOT delete or modify `AGENTS.md` / project `CLAUDE.md`**

These files are read by AI tools other than Claude (Gemini, Copilot, ChatGPT, etc.).
Promoting knowledge from `AGENTS.md` to `~/.claude/knowledge/` does not require
removing it from `AGENTS.md` — the duplication is intentional because the
audiences are different and is therefore not an SSoT violation.

## Step 7: Report the Work Summary

Report to the user in this format:

```
## Knowledge Audit Results

### Promoted (→ knowledge/)
- `knowledge/xxx.md` created or updated: <one-line description>
- CLAUDE.md trigger table updated: yes / no (reason)

### Policy Audit findings
- None / <candidate>: <reason Skill migration is recommended>

### Demoted (→ project memory)
- None / <target>

### Promotion declined
- <candidate>: <reason — which gate check failed>

### Unchanged
- AGENTS.md (SSoT exception — other AI tools read this file)
```
