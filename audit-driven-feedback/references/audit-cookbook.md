# Audit Cookbook — Implementing & Wiring

How to build an audit that earns its place and stays trustworthy, then wire it into
the reconciliation loop. Stack-neutral; map the patterns onto the target project's
task runner, CI, and scheduler.

## Anatomy of a good audit

Build every audit to these five properties (summarized in SKILL.md, expanded here).

### 1. Enumerate the set, not a sample
The value of an audit is catching the member nobody remembered. So it must derive the
full set from a **source of truth** — the framework's own route/event registry, a
generated spec, a schema query, a file glob — not a hardcoded list that itself drifts.
If you find yourself maintaining the list by hand, the list is now a second thing to
audit; fix the enumeration instead.

### 2. Deterministic
Same repo state ⇒ same verdict. No dependence on wall-clock, network flakiness,
iteration order, or test data left lying around. A flaky audit is worse than none: the
first false red trains everyone to ignore it. If an audit can't be made deterministic,
it's probably a monitoring concern, not an audit.

### 3. Exit non-zero on violation
The audit is a command whose exit code is its verdict: `0` clean, non-zero dirty. This
is what lets CI block a merge and a scheduler trigger an alert without any glue. Print
human-readable detail to stdout/stderr alongside the exit code.

### 4. Actionable message — the most underrated property
For each violation, print **where** it is and **what to do**. Compare:

- Bad: `3 violations found`
- Good:
  ```
  ✗ route `admin.users.destroy` has no authorization
      → if intentionally public, add it to config audit.auth_exempt
      → otherwise attach an auth/permission middleware
  ```

This matters for humans, and *doubly* for AI agents: when an agent runs the audit and
reads the failure, the message **is** its fix instruction. A well-worded audit turns
the agent into a competent controller of the loop. Invest in these strings.

### 5. Declared exemptions
Real systems have legitimate exceptions (a genuinely public endpoint, a config key
that's intentionally write-only). Put them in an explicit, version-controlled,
reviewed allowlist — a config entry, an annotation, a dedicated file. Benefits:
- the audit stays at **zero** violations, so any non-zero is a real signal
- adding an exemption becomes a visible diff a reviewer must approve
- the allowlist documents the system's intentional exceptions in one place

Never suppress a violation by weakening the check ("skip routes starting with
admin"); suppress it by naming the specific exempt member.

## Make it a first-class command

Implement the audit inside the project's own tooling so it's runnable identically by a
human, by CI, and by an agent:

- a CLI subcommand / framework console command (`<tool> audit:<name>`)
- or a make target / package script / task-runner task

Group related audits under a namespace and add an umbrella command that runs them all
and aggregates exit codes — this becomes the "health check" the agent runs.

```
# umbrella: run all audits, fail if any fails
audit:all  ->  runs audit:parity-routes, audit:wiring-events, audit:docs, audit:data...
               exit non-zero if ANY sub-audit failed
```

## Wiring: two tiers

The *same* audit serves two purposes depending on when it runs.

### CI = prevention (per PR)
Run the relevant audits on every pull request; a violation blocks merge. This stops
drift from ever reaching the main branch. Keep CI audits fast and deterministic so
they don't become a bottleneck people route around.

```yaml
# illustrative — adapt to the project's CI
on: [pull_request]
steps:
  - <install deps>
  - run: <tool> audit:all
```

### Scheduled = recovery (periodic, full-scope)
Run on a timer (e.g. nightly) over the whole codebase, and — critically for **Data**
audits — against production data, where drift appears even with frozen code. The key
requirement: **failure must be observable**. A scheduled audit whose red nobody sees
is not a closing loop.

```
# illustrative — adapt to the project's scheduler
schedule "audit:data" daily at 03:00
  on_failure -> notify(team_channel)     # the loop opened; make a human/agent see it
```

Pick the tier per audit type:
- **Parity / Wiring / Docs / Config / Architecture / Process** → mainly CI (they're
  about *code* state, fully determined by the repo).
- **Data** → mainly scheduled against live data (and optionally CI against fixtures).

## Closing the loop with an AI agent

Give the agent a standing instruction and let it be the controller:

```
1. Run `<tool> audit:all`.
2. For each failure, read the message, locate the cause, fix it
   (prefer fixing the code that produced the drift, not silencing the audit).
3. Re-run `<tool> audit:all`. Repeat until green.
4. If an exemption is genuinely warranted, add it to the allowlist (a reviewable diff),
   not by weakening the check.
```

Because property #4 (actionable messages) makes each failure self-describing, the
agent can usually resolve it without further context. This is the payoff: the loop
runs mostly autonomously, and humans step in only to define the desired state and to
approve exemptions.

## Growing the audit suite (do NOT front-load)

Restating the most important operational rule, because it's where audit cultures fail:
**add audits from postmortems, not from imagination.** When an incident happens, ask
"what one check would have caught this?", implement exactly that, wire it, done. A
suite grown this way has a high hit rate and obvious justification for every entry. A
suite grown from "let's be thorough" fills with checks that never fire or fire wrong,
and the noise eventually discredits the whole practice.

And **inventory before you add.** Before writing a new audit, check whether the drift
is already covered by an existing audit/test/CI gate, whether an existing audit can be
*extended* instead, and whether existing guardrails are actually wired and running. A
mature suite fails in a recognizable way: audits accrete (`audit_a`, `audit_b`,
`audit_c`…) until no one knows the whole set — that loss of overview is itself drift.
This is the same reflex as `kubectl get` / `terraform state list` before adding a new
controller: see what already manages the surface, then decide if you need new control.

Prune, too: if an audit hasn't caught anything in a long time and the risk it guards is
gone, removing it is legitimate maintenance — fewer, sharper audits beat many dull ones.
