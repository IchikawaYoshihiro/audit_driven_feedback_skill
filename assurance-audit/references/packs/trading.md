# Domain pack — trading system (the reference pack)

This pack maps a live-trading codebase onto the generic engine. It doubles as a
**Rosetta stone**: it shows how the trading-specific vocabulary (`R-N`, "market closed",
tick-size) becomes the generic terms (Protected Behavior, Inventory, Detective/Preventive).
A reader who has never seen the trading repo can still learn the engine from here.

It also carries a **golden matrix** (§6): re-running assurance-audit with this pack
against that repo must reproduce those colors. That is the skill's first regression test.

> This pack is distilled from a real audit (`failure_mode_audit_2026-06-20.md`) of an
> auto-trading system, and from the two project skills it generalizes (`test-audit`,
> `failure-mode-audit`).

---

## 0. Inventory location (Step -1)

Where the ledger of protected behaviors lives in this domain:

- **Primary**: `docs/safety/known_risks.md` — each `### R-N.` heading is one post-incident
  control ("R-N" = a regression-prevention control born from a postmortem, not just a bug).
- **Secondary**: `docs/operations/postmortems/*`, `docs/safety/failure_modes.md` (itself an
  audit artifact — never hand-edit it).
- **Fallback taxonomy** if no ledger exists: §2 below.

## 1. Ledger source & enumeration (Step 0)

```bash
grep -n "^### R-" docs/safety/known_risks.md   # one Protected Behavior per heading
```

Skip "unimplemented capability" placeholders (e.g. R-10–R-14 priority-table rows). A
heading present = some implementation exists to grade.

## 2. Standard taxonomy (Step -0.5 yardstick + Step 1 categories)

Diff the ledger against this list to find Inventory gaps; the **market-closed** behavior
below was discovered exactly this way — it was a real failure mode *absent from the ledger*.

- **Execution**: duplicate entry / partial fill / orphaned exit leg / abnormal fill price (tick-size)
- **Market Data**: feed disconnect (PUSH / bar stall) / rate limit (429) / market-closed · calendar
- **Operations**: wiring gap / notification gap (aggregate) / audit gap (signal silence)
- **Risk**: capital exhaustion / mis-order (size, balance)
- **Compliance**: same-day settlement (差金決済) regulation

## 3. Criticality rubric (Step 4, ordering only — never changes color)

**High** = touches order placement, settlement, or capital. Everything else Med/Low.

## 4. What Preventive vs Detective looks like here

| Behavior | Preventive (blocks before commit) | Detective (notices after) |
| --- | --- | --- |
| duplicate entry | `AlreadyHoldingRule` / `SameDayReentryRule` / `MaxInflightEntriesRule` (RiskGate reject) | — |
| capital exhaustion | `CashLossBudgetRule` (fail-secure REJECT) | — |
| market-closed | *(none — could be a trading-calendar pre-check)* | `liveness` monitor (treats 1d-bar presence as the truth of a business day) |
| feed disconnect | — | `force_close_timer` + `stale_monitor` |
| wiring gap | — | `audit_wiring.py` + parity test |

## 5. Test discovery recipe (Step 2, function-granular)

Search by **control class** and by **Expected Outcome / behavior string**, not by the R-N tag:

```bash
uv run python3 -c "
import re
from pathlib import Path
rx = re.compile(r'CashLossBudgetRule|already_holding|reason\s*==')  # control + behavior
total = 0
for p in Path('tests').rglob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    for f in re.split(r'(?m)^\s*(?=(?:async )?def test_)', text):  # ^\s* catches TestCase methods
        if rx.search(f): total += 1
print(total)
"
```

The two canonical false-positives this avoids (see
[../grading-rubric.md](../grading-rubric.md) §4): the R-15 tag returned 0 tests but the
control class `CashLossBudgetRule` returned 34; `duplicate` returned nothing but the
behavior assertion `reason == "already_holding"` exists.

---

## 6. Golden matrix (regression reference)

Running assurance-audit + this pack against the source repo must reproduce the
**Status colors and the two 🟡 findings** below — totals **13 behaviors · Missing Control 0
· 🟢 11 / 🟡 2 / 🔴 0.**

> **Assert on colors, not on the exact integers.** The test counts came from a human
> auditor reading *dedicated and adjacent* test files (e.g. `CashLossBudgetRule` → 34 across
> five files). A literal-symbol-per-function `grep` gives a smaller number (2), the dedicated
> file alone gives 9 — all three still resolve to "≥2 Strong → 🟢". Count is a triage signal,
> not the verdict; the color is the invariant. (This drift between counting methods is itself
> a lesson — never pin a Status to one mechanical count.)

| Category | Behavior → Expected Outcome | Control (strength) | Tests | Quality | Status | Crit |
| --- | --- | --- | --:| --- | --- | --- |
| Execution | double entry → duplicate same-symbol entry is rejected | AlreadyHolding+SameDayReentry+MaxInflight (Preventive) | 9 | Strong | 🟢 | High |
| Execution | partial fill → partially-filled orders are tracked | ExecutionRecord / is_partially_filled (Detective+handling) | 4 | Strong | 🟢 | High |
| Execution | orphaned exit leg → no exit leg is left unmatched | ExitReconciler + orphan sweep (Preventive+Detective) | 14 | Strong | 🟢 | High |
| Execution | abnormal fill price → off-tick fills are corrected | FillModel tse_standard (Preventive, **backtest only**) | 12 | Strong | 🟡 | Med |
| Market Data | feed disconnect → stalled bars force a safe close | force_close_timer + stale_monitor (Detective) | 34 | Strong | 🟢 | High |
| Market Data | rate limit 429 → bursts back off instead of flooding | retry/backoff + warmup throttle (Preventive) | 7 | Strong | 🟢 | Med |
| Market Data | **market-closed** → no order is placed on a non-trading day | liveness, 1d-bar proxy (**Detective only**) | 0 prev. | — | **🟡 Structural Weakness** | High |
| Operations | wiring gap → every defined hook is actually wired | audit_wiring.py + parity test (Detective) | 12 | Strong | 🟢 | High |
| Operations | aggregate notification gap → failed symbols are listed in the alert | force_close_manager aggregate notice (Detective) | 2 | Strong¹ | 🟢 | Med |
| Operations | signal silence → a strategy going quiet is detected | liveness_monitor (Detective) | 33 | Strong | 🟢 | High |
| Risk | capital exhaustion → projected max loss ≤ cash×(1−buffer) | CashLossBudgetRule (Preventive) | 34 | Strong | 🟢 | High |
| Risk | mis-order (size/balance) → orders over available cash are rejected | CashBalanceRule (Preventive) | 6 | Strong | 🟢 | High |
| Compliance | same-day settlement → 差金決済 orders are blocked | R-8 guard (Preventive) | 8 | Strong | 🟢 | High |

¹ Was 🔴 Weak originally (asserted "processing continues", not the aggregate body); fixed
2026-06-21 by adding a test that asserts the failed-symbol list directly.

### The two 🟡 — both are *Structural Weakness*, both are the engine earning its keep

- **market-closed**: a failure mode that *was not in the ledger at all* (Step -0.5 Threat
  Discovery found it) **and** has only a Detective control where a Preventive trading-calendar
  pre-check is achievable → 🟡 + a new-candidate-risk (proposed as R-20). This single finding
  is why Inventory Audit and Threat Discovery are separate steps.
- **abnormal fill price (live)**: Preventive exists for backtest (`FillModel`) but the
  live pre-order guard is unconfirmed → can't claim Preventive on the live path → 🟡.

### Candidate Discovery (Step 5) reproduced here

- New candidate: **market-closed / calendar** (no R-N) → propose ledger entry R-20.
- Orphan tests: none found.
