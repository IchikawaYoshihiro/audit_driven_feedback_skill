# Writing a domain pack

The engine in `SKILL.md` is domain-agnostic. A **domain pack** is the only thing that
changes between a trading system, a web API, and a SaaS billing service. It supplies the
domain's vocabulary and recipes; the grading logic and the rubric stay fixed.

A pack is one Markdown file under `references/packs/<domain>.md`. Copy
[packs/trading.md](packs/trading.md) — the reference pack — and replace its six sections.

## What a pack must supply

| # | Section | Feeds | What to write |
| --- | --- | --- | --- |
| 0 | **Inventory location** | Step -1 | Where the ledger of protected behaviors lives in this domain (threat model / ADR / known-risks / runbook / postmortems), and the fallback taxonomy to use if none exists. |
| 1 | **Ledger source & enumeration** | Step 0 | The exact file(s) and the command to list one Protected Behavior per entry. |
| 2 | **Standard taxonomy** | Step -0.5 + Step 1 | The canonical category list for this domain. This is the *yardstick* Threat Discovery diffs the ledger against — so make it the list a domain expert would expect, including the easily-forgotten items. |
| 3 | **Criticality rubric** | Step 4 (ordering) | What counts as High/Med/Low impact. Ordering only — never changes a Status color. |
| 4 | **Preventive vs Detective examples** | Step 1 | A small table of real controls in this domain, each labeled — so the grader recognizes the shapes. |
| 5 | **Test-discovery recipe** | Step 2 | A function-granular counting snippet for this stack, searching by **control identifier *and* Expected Outcome / behavior string** (not just a ledger tag). |
| 6 | **Golden matrix** *(optional but recommended)* | regression | A known-good run: behaviors → Expected Outcome → Control → Status. Assert on **colors**, not exact counts. |

## Design rules

- **The taxonomy is the most valuable thing you write.** Threat Discovery is only as good as
  the list it diffs against. A thin taxonomy hides exactly the forgotten behaviors the audit
  exists to find. Err toward listing the unglamorous ones (password-reset abuse, webhook
  replay, idempotency-on-retry) — those are what real ledgers omit.
- **Every behavior gets an `Expected Outcome`.** A pack's examples should always be written
  `Behavior → Expected Outcome` (e.g. "authz bypass → an unauthorized user gets 403"), never
  a bare noun. The Expected Outcome is what Step 2 searches for and Step 3 grades against.
- **Pin Preventive vs Detective to *your* domain's idioms.** "Logging is detective" is the
  rule, but the grader needs to see *your* preventive guards (a 403 from a policy gate, a
  `UniqueConstraint`, an `IdempotencyKey`) vs *your* detective ones (an audit log, an alert,
  a reconciliation job) to apply it fast.
- **Recipes search by behavior, not by tag.** The single most common false verdict is a
  tag/class-name search returning 0 and being read as "no test." Bake the Expected-Outcome
  search into the recipe so the pack can't be used the lazy way. (See
  [grading-rubric.md](grading-rubric.md) §4.)
- **Don't restate the rubric.** Control/Quality/Status definitions live only in
  `grading-rubric.md`. A pack supplies *examples* of each level in its domain, not new
  definitions.

## Minimal skeleton

```markdown
# Domain pack — <domain>

## 0. Inventory location (Step -1)
- Primary: <where the ledger lives>
- Fallback taxonomy if none exists: §2

## 1. Ledger source & enumeration (Step 0)
<command that lists one Protected Behavior per entry>

## 2. Standard taxonomy (Step -0.5 + Step 1)
- <Category>: <behavior> / <behavior> / <the forgotten one>
- ...

## 3. Criticality rubric (Step 4, ordering only)
High = <touches money / auth / data integrity>. Else Med/Low.

## 4. Preventive vs Detective in this domain
| Behavior | Preventive | Detective |
| --- | --- | --- |
| ... | ... | ... |

## 5. Test-discovery recipe (Step 2, function-granular)
<snippet searching by control id AND Expected Outcome>

## 6. Golden matrix (optional)
| Behavior → Expected Outcome | Control (strength) | Status |
```
