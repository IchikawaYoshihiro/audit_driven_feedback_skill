---
name: assurance-audit
description: >-
  Audit whether a system's protected behaviors are actually guarded by controls and
  evidenced by trustworthy tests — an Assurance Audit, not a Coverage Audit. Use when the
  question is not "how much is tested" but "is the thing that must not happen actually
  prevented, and is the test that proves it real or theater?" Grades each behavior along
  Inventory → Threat Discovery → Control (None/Detective/Preventive) → Test
  (function-granular) → Quality (Strong/Weak) → Status (Missing/Stale Control, Weak Test,
  Structural Weakness, SPOF, OK). Trigger on: "is this control actually tested", "are our
  guardrails real", mock-hidden or theater tests, "we have coverage but I don't trust it",
  threat-model vs test reconciliation, protections that exist but aren't enforced, or
  auditing security/billing/trading/safety controls. Domain-agnostic core with swappable
  packs (trading, web-security, saas-billing). Complements audit-driven-feedback, which
  decides what to audit and wires it into CI; this grades whether a protection holds.
---

# Assurance Audit

> Assurance Audit verifies that intended behaviors are protected by controls and
> evidenced by trustworthy tests.

## What this is — and what it is not

This is **not a Coverage Audit.** "80% coverage / 1,200 tests / good unit:e2e ratio"
tells you how *much* is tested. It tells you nothing about whether the 20% that isn't —
or even the 80% that is — actually protects the behaviors that must never break. A
codebase can be 95% covered and still ship a guard that a mock quietly defeats, or a
"fixed" incident whose regression test asserts the wrong thing.

An **Assurance Audit** asks, for each thing that must not happen: *is there a control,
does it prevent or merely detect, is there a test, and does that test assert the real
outcome or just a side effect?* It grades **Confidence**, not coverage:

```
Inventory → Threat Discovery → Behavior → Control → Test → Quality → Status
   (does a   (is the ledger    (intent)   (None/     (func-  (Strong/  (color)
    ledger     sufficient?)                Detective/ count)   Weak)
    exist?)                                Preventive)
```

The model underneath is `Intent → Behavior → Control → Evidence`. Coverage stops at
"Evidence exists." Assurance asks "is the Evidence trustworthy, and does the chain hold
all the way back to Intent?"

### How this relates to `audit-driven-feedback` (say this if asked)

They are complementary, not overlapping:

- **audit-driven-feedback** — *what* to audit and *how to wire it*: diagnose drift (7
  audit types), implement a check, wire it into CI (prevent) + scheduled (recover),
  close the detect→fix→re-audit loop.
- **assurance-audit** (this skill) — the **grading engine**: given a protection, *is it
  really tested, and is the test real or performance?* It produces the per-behavior
  verdict (None/Detective/Preventive · Strong/Weak · Status) that the other skill's loop
  acts on.

## The rubric is canonical and lives in one file

All three scoring tables — Control strength (None/Detective/Preventive), Test quality
(Strong/Weak), and Status — live in **[references/grading-rubric.md](references/grading-rubric.md)**.
Read it before grading. Do not restate the tables elsewhere; if two copies existed they
would drift and no verdict could be trusted. (Same discipline the trading project uses by
keeping its Quality table in one skill file referenced by the other.)

## Domain packs (the only swappable part)

The engine is domain-agnostic. Everything trading/web/billing-specific lives in a
**domain pack** under `references/packs/`. A pack supplies: where the ledger lives, how to
enumerate behaviors, the standard taxonomy (the Threat-Discovery yardstick), the
Criticality rubric, the test-discovery recipe for that stack, and what Preventive vs
Detective concretely look like. To write your own, follow
**[references/domain-pack-guide.md](references/domain-pack-guide.md)**.

Shipped packs:

- **[packs/trading.md](references/packs/trading.md)** — the reference pack & Rosetta stone;
  carries a golden matrix used as the skill's own regression test.
- **[packs/web-security.md](references/packs/web-security.md)** — authz bypass, duplicate
  registration, IDOR, rate limit.
- **[packs/saas-billing.md](references/packs/saas-billing.md)** — plan-limit bypass, double
  charge, audit-log gap.

At the start of a run, ask which pack applies (or infer it from the repo). If none fits,
use the closest pack's taxonomy as a starting yardstick and tell the user a custom pack
would sharpen Threat Discovery.

---

## Workflow

A 4-layer model: **Inventory → Threat Discovery → Control → Test → Quality**, then Status,
Candidate Discovery, Report. The historical progression behind it — "count tests" →
"look at controls" → "look at whether the *ledger of what to protect* even exists" — is
why the first two steps come before any grading.

### Step -1 — Inventory Audit: does a ledger even exist?

Before grading anything, find out whether the project has **an enumerated list of behaviors
that must be protected**. In the real world the biggest defect is rarely a weak control —
it's that *no one ever listed what to protect*. ("Authz bypass" and "double charge" are
obvious; "password-reset abuse" and "email-resend spam" get forgotten.)

Locate the ledger (the pack says where: threat model / ADR / known-risks / runbook /
postmortems). **If it is missing or thin, that absence is the top-priority Gap** — report it
above any control finding, then fall back to the pack's standard taxonomy as a provisional
ledger so you can still proceed. (This mirrors audit-driven-feedback's "inventory existing
guardrails first," applied to the *things being protected* rather than the guards.)

### Step -0.5 — Threat Discovery: is the ledger *sufficient*?

A ledger existing is not a ledger being complete. Diff it against the pack's **standard
taxonomy** and report the delta as **Inventory Coverage**. Example: a SaaS has
`billing_rules.md` that mentions only "double charge" while plan-limit bypass, webhook
replay, and free-trial abuse are real and unlisted.

This is where the highest-value findings often come from: `Failure mode exists ∧ Inventory
missing`. (In the reference pack, the "market-closed" failure mode was real, had only a
detective control, and **was absent from the ledger** — found here, not by grading controls.)
Feed the delta into Step 5 as new candidates.

### Step 0 — Load Protected Behaviors

Enumerate behaviors from the ledger (plus anything Threat Discovery added). Each is one
scoring row. **Give every behavior an explicit one-line `Expected Outcome`** — the
observable thing you want guaranteed or prevented (e.g. "an unauthorized user gets 403";
"a duplicate request bills exactly once"). The Expected Outcome is the search key for Step 2
and the bar for Strong in Step 3. Without it, "is it tested?" has no precise meaning.

### Step 1 — Control Audit: grade strength

For each behavior, find its guard in the code and grade it **None / Detective / Preventive**
(see the rubric). Does the mechanism run *before* the dangerous action and stop it
(Preventive), or *after* and merely observe it (Detective)? Logging is Detective.

**Do not conclude `None` from a `grep` miss** — re-search by the control's concrete
identifier and by the Expected Outcome (rubric §4).

### Step 2 — Test Discovery: count at function granularity

Find the tests, counting **per test function**, not per file — one big file can match a
search while a single function actually exercises the behavior. Search by the **control's
identifier *and* the Expected Outcome / behavior string**, not just a ledger tag. The
canonical proof this matters: a class-name search returning 0 while the behavior-string
search returns several real tests (rubric §4). A function-splitting snippet lives in each
pack's test-discovery recipe.

### Step 3 — Quality Audit: Strong or Weak

Read the tests and grade each Strong vs Weak (rubric §2). Strong = directly asserts the
Expected Outcome. Weak = asserts only a side effect, hides the subject behind a mock, or
covers it only indirectly — any one makes it Weak, and **Weak overrides Count**.

### Step 4 — Status

Combine Control × Count × Quality into one color (rubric §3): 🔴 Missing / Stale Control /
Weak Test · 🟡 Structural Weakness / SPOF · 🟢 OK. **Keep Status (health) separate from
Criticality (impact)** — Criticality only orders the fixes; it never changes a color.
Flag **Structural Weakness** wherever `Expected Control = Preventive ∧ Actual = Detective`
(prevention is achievable but the system only detects after the fact).

### Step 5 — Candidate Discovery (reverse + new)

1. **New candidates** — behaviors surfaced in Threat Discovery with no ledger entry. These
   are the next entries to register; put them *first* in the report (the unique value of the
   control axis over a tag-only audit).
2. **Orphans** — test tags/markers that reference a ledger item that no longer exists
   (renumbered, deleted, or typo'd).

### Step 6 — Report

Lead with **New Candidate Risks** (and any missing/thin Inventory from Step -1), then the
per-behavior matrix (by category), then Gap detail ordered:
**Inventory gap → Missing Control → unregistered risk → Structural Weakness → Stale Control
→ Weak Test.** For each Gap give one or two lines: what is unprotected and how a regression
would be noticed. Propose the biggest, independently-actionable items as follow-up tasks.

---

## Anti-patterns to watch for

- **Reading a `grep` 0 as "doesn't exist"** — in either direction (control *or* test). It is
  a trigger to drill by identifier and Expected Outcome, never a conclusion (rubric §4).
- **Counting files, not functions** — misses the one function in a 46-function file.
- **Treating Detective as Preventive** — "we get alerted" is not "it can't happen."
- **Letting Count beat Quality** — ten mock-hidden tests are still 🔴.
- **Mixing Criticality into Status** — a low-impact gap is still 🔴; impact only sets order.
- **Auditing controls before checking the ledger exists** — the absent behavior is the one
  you'll never grade. Steps -1 and -0.5 come first.
- **Pitching this as a coverage tool** — it grades trustworthiness of protection, not volume.
- **Restating the rubric** — keep it only in references/grading-rubric.md.
