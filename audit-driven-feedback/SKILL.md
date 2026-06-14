---
name: audit-driven-feedback
description: >-
  Introduce and operate Audit-Driven Feedback Development — a reconciliation-loop
  method that keeps a codebase internally consistent when AI agents do most of the
  implementation. Use whenever the user wants to catch silent integrity drift:
  wiring gaps (a feature added but its listener/notification never wired), doc drift
  (docs reference deleted code), config drift (.env vs config), parity gaps
  (routes without authorization, endpoints missing from the API spec), or broken data
  invariants — defects that pass tests AND review yet quietly break in production.
  Trigger on mentions of audits, guardrails, drift detection, integrity/consistency
  checks, "things silently breaking", turning a postmortem into an automated check,
  stopping AI agents from leaving inconsistencies, or wiring integrity checks into CI
  and scheduled jobs. Covers diagnosing what to audit (7 audit types), implementing
  it, wiring into CI (prevention) + scheduled runs (recovery), and closing the
  detect → fix → re-audit loop. Language/framework-agnostic.
---

# Audit-Driven Feedback Development

## What this is

Tests verify that *individual behaviors* are correct. They do nothing about
*system-wide consistency* eroding over time. When AI agents implement most changes,
the dangerous failures are not crashes — those get caught — but **silent integrity
drift**: the feature works, but the notification was never wired; the endpoint
returns correctly, but the API spec wasn't updated; the code is new, but the docs
still point at a deleted class. Each PR looks correct in isolation, so review misses
it. It surfaces months later as "why didn't the alert fire?"

This skill helps you install a **reconciliation loop**: define the desired state,
observe the actual state with automated *audits*, detect the gap, fix it, and
re-audit — then feed every new incident back in as the next audit.

```
incident → postmortem → add audit → CI (prevent) + scheduled (recover)
   → detect drift → fix → re-audit → (next incident feeds back in)
```

**The audit is a sensor, not the point.** The point is the loop that keeps closing.
Do not let this become "write as many audits as possible."

### How audits relate to tests (say this if the user pushes back)

- A test checks **"behavior X is correct"** — but only for the cases you remembered
  to write. A route you forgot to test is invisible to tests forever.
- An audit checks **"the whole set has no holes"** — it enumerates *all* routes /
  endpoints / events and asserts none are missing authorization / spec entries /
  listeners. It catches **absence**: the thing nobody wrote, wired, or updated.

Audits do not replace tests. They cover the layer *outside* tests. Recommend both.

## The 7 audit types (use this to diagnose what to audit)

This taxonomy is the diagnostic lens. When a user describes a pain point, name the
type — it tells you what two things to compare and how to enumerate the set.

| Type | Protects against | Compares |
| --- | --- | --- |
| **Parity** | one side of a required pair missing | route ↔ authz middleware, endpoint ↔ API spec, enum ↔ DB values |
| **Wiring** | something built but not connected | service ↔ notification, event ↔ listener, job ↔ queue registration |
| **Data** | broken invariants in stored state | "deleted user has no active orders", "total == sum(lines)" |
| **Docs** | documentation drift | docs ↔ code (referenced class/route/file still exists) |
| **Config** | environment/config divergence | `.env.example` ↔ loaded config keys, per-env config parity |
| **Architecture** | layering/dependency rule violations | domain layer ↔ does not import infra; allowed dependency direction |
| **Process** | gaps in the development process itself | endpoint ↔ has a test, public API ↔ has a changelog entry |

For per-type detection recipes (how to enumerate the set, typical violations,
pseudocode sketches), read **[references/audit-types.md](references/audit-types.md)**.

## Workflow

When this skill triggers, the user is usually in one of three entry points. Identify
which, then converge on the same path: **inventory → diagnose → prioritize → implement
→ wire → close the loop.**

### Step 0 — Identify the entry point

- **Incident-driven** ("we just got burned by X / here's a postmortem"): the best
  entry point. One real incident → one targeted audit (Diagnose from a postmortem).
- **Pain-driven** ("things keep silently breaking / set up guardrails"): a scoped cold
  scan — but resist auditing everything.
- **Review-only** ("what *should* I be auditing?"): diagnose and deliver a prioritized
  candidate list, then stop before implementing unless asked.

### Step 1 — Inventory existing guardrails first

**Before proposing any new audit, take stock of what already guards this codebase**:
existing audits/health-checks, the test suite, CI gates, lint/arch rules, scheduled
ops checks, runtime monitors. For each candidate you're about to suggest, ask:

- Is this drift *already* covered by something here? (then don't duplicate it)
- Can an existing audit be *extended* to cover it, instead of adding a new command?
- Is the existing guardrail actually *wired and running*, or does it exist but isn't
  invoked anywhere? (a defined-but-unrun audit is itself a Wiring gap — surface it)

This step exists because mature audit cultures fail in a specific way: audits keep
accreting (`audit_a`, `audit_b`, `audit_c`…) until nobody knows the whole set — which
is itself a form of drift. The discipline mirrors GitOps/infra practice: you run
`kubectl get` / `terraform state list` to see what existing controllers already manage
*before* writing a new one. Observe the current control surface, then decide whether
you need new control or just need to extend/wire what's there.

Often the highest-value finding is not "add an audit" but "you already have the right
audit — it just isn't running in CI" or "two existing audits overlap; merge them."

### Step 2 — Diagnose what to audit

**From a postmortem (preferred).** Take the actual incident and ask: "what single
check, had it existed, would have caught this before it shipped?" That check is the
audit. This is the highest-hit-rate way to choose audits — grounded in a failure that
really happened, not in imagination. Name its type, then implement exactly that one.

**From a cold scan (pain-driven / review-only).** Inspect the project against the 7
types and surface a *small* set of high-value candidates: routes/endpoints without
authorization, events without listeners, notifications defined but never dispatched,
docs referencing code, `.env` keys not in config (or vice-versa), data tables with
obvious invariants (totals, soft-delete relationships), layering rules stated in docs
but unenforced. Present candidates as a table: *type · what it checks · why it matters
· effort*. **Do not implement all of them** — that's the next step.

### Step 3 — Prioritize (the most important step)

**Audits are not free, and more is not better.** Over-auditing causes:
- false positives → red builds → "cry wolf" → people ignore audits
- noise that buries the one audit that actually mattered
- maintenance cost → the audit itself drifts and becomes a liability

Rule of thumb: **grow audits from real incidents, not from a wish to be thorough.**
A postmortem-sourced audit earns its keep; a speculative one usually doesn't fire,
or fires wrong. When in doubt, implement fewer and let incidents pull the rest.

### Step 4 — Implement the audit

A good audit has five properties. Build to these — details and examples in
**[references/audit-cookbook.md](references/audit-cookbook.md)**.

1. **Enumerates the set, not a sample** — it walks *all* routes/events/files, so it
   catches the one nobody remembered.
2. **Deterministic** — same repo state → same result. No flakiness; a flaky audit
   gets disabled within a week.
3. **Exits non-zero on violation** — so CI and schedulers treat it as a failure.
4. **Reports an actionable message** — names each violation *and what to do about it*
   ("route `X` has no authz; if intentionally public add it to the exempt list,
   otherwise add auth middleware"). This matters doubly when an AI agent consumes the
   output to self-correct — the message becomes its fix instruction.
5. **Allows declared exemptions** — legitimate exceptions live in an explicit,
   reviewed allowlist (e.g. a config file), so the audit stays at zero-violations and
   any new exemption is a visible diff.

Implement it as a first-class command in the project's own task runner (a CLI
subcommand / make target / npm script / artisan command — whatever the stack uses),
not a throwaway script. It must be runnable by a human, by CI, and by an agent.

### Step 5 — Wire it (two tiers)

The same audit plays two roles depending on *when* it runs:

- **CI = prevention.** Run on every PR; block merge on violation. Stops drift before
  it reaches the main branch.
- **Scheduled = recovery.** Run daily/periodically over the full codebase (and, for
  Data audits, against production data) to catch drift that slipped past CI or arose
  from outside the code path. **Make failure observable** — route it to a
  notification channel so someone actually learns the loop opened.

### Step 6 — Close the loop

Detect → fix → **re-run the same audit** to confirm it passes. Never leave a detected
violation un-reverified. For AI-agent workflows, bundle the audits into a single
"health check" command and give the agent a standing instruction: *run it, fix any
failure, re-run until green.* That turns the agent into the controller of the loop.

Finally, when a new incident occurs, return to Step 2 (diagnose from the postmortem).
The loop's long-term value is this feedback edge: incidents become audits, so the same
failure cannot recur silently.

## Anti-patterns to watch for

- **Skipping the inventory** — adding an audit that duplicates an existing one, or
  writing a new audit when an existing one merely wasn't wired into CI. Look first.
- **Audit sprawl** — audits accreting unbounded until no one knows the full set. That
  loss of overview is itself drift; periodically inventory and prune.
- **Auditing everything up front** — see the Prioritize step. Start from incidents.
- **Audits that sample instead of enumerate** — defeats the whole purpose (the gap is
  in the part you didn't look at).
- **Silent failure** — a scheduled audit whose failure nobody sees is not a loop.
- **Vague messages** — "3 violations found" with no location or remedy wastes both
  humans and agents. Always say *where* and *what to do*.
- **Pitching it as a TDD replacement** — it is the layer outside tests, not a rival.
