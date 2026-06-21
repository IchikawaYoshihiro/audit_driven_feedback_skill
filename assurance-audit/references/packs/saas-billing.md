# Domain pack — SaaS billing & entitlements

Maps a subscription/billing service's money-and-entitlement behaviors onto the generic
engine. Same `Inventory → Threat Discovery → Control → Test → Quality → Status` flow; only
the vocabulary and recipes below are domain-specific. Billing bugs are unusually expensive
and unusually quiet — a missing idempotency key double-charges in production while every
test stays green — so the Strong/Weak distinction matters most here.

---

## 0. Inventory location (Step -1)

- **Primary**: a billing spec / pricing-rules doc / entitlement matrix (plan → features →
  limits). Often only a Stripe dashboard exists with **no written ledger** — that absence is
  the top Gap.
- **Secondary**: billing-incident postmortems, refund/chargeback tickets, the webhook handler
  itself (the de-facto spec).
- **Fallback taxonomy** if no ledger exists: §2.

## 1. Ledger source & enumeration (Step 0)

Enumerate from the entitlement matrix and the set of money-moving operations (charge,
refund, proration, trial conversion, plan change). Give each an Expected Outcome:

- double charge → *the same payment intent / request bills exactly once*
- plan-limit bypass → *creating the (limit+1)-th resource is rejected*
- trial conversion → *a trial converts to paid exactly once, at the right time*

## 2. Standard taxonomy (Step -0.5 yardstick + Step 1 categories)

The forgotten ones (⚠) are what Threat Discovery should surface — real ledgers usually list
only "double charge":

- **Charge integrity**: double charge on retry / ⚠ webhook **replay** billing twice / ⚠
  partial-failure leaving a charge without a fulfilled entitlement
- **Entitlement**: plan-limit bypass (seats, API calls, storage) / ⚠ entitlement not revoked
  on downgrade or cancellation / ⚠ feature accessible after expiry
- **Lifecycle**: ⚠ free-trial abuse (repeat trials, multi-account) / proration miscalculation
  / dunning not retrying failed payments
- **Audit & reconciliation**: ⚠ **billing audit-log gap** (a charge with no immutable record)
  / ledger-vs-provider (Stripe) drift

## 3. Criticality rubric (Step 4, ordering only)

**High** = anything that moves money or grants/denies paid access (charge, refund,
entitlement). Med = reporting/reconciliation. Low = cosmetic. Ordering only.

## 4. Preventive vs Detective in this domain

| Behavior | Preventive (blocks before commit) | Detective (notices after) |
| --- | --- | --- |
| double charge | **`IdempotencyKey`** rejecting the replayed request | nightly duplicate-charge report |
| webhook replay | event-ID dedup table checked before processing | alert on repeated event IDs |
| plan-limit bypass | quota check **before** resource creation | usage-overage report |
| entitlement after cancel | access check against current subscription state | audit of active entitlements |
| audit-log gap | write-then-charge transaction (no charge without a record) | reconciliation job vs provider |

An **`AuditLogger`** that *records* a charge is Detective evidence; it does not *prevent*
the double charge. Idempotency is the Preventive control.

## 5. Test-discovery recipe (Step 2, function-granular)

Search by **Expected Outcome** ("bills once", quota rejection) and the **control identifier**,
not by an endpoint name:

```bash
python3 -c "
import re
from pathlib import Path
rx = re.compile(r'[Ii]dempotenc|charged?_once|call_count\s*==\s*1|assert_called_once|QuotaExceeded|over_limit|webhook.*dedup')
total = 0
for p in Path('tests').rglob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    for f in re.split(r'(?m)^\s*(?=(?:async )?def test_)', text):
        if rx.search(f): total += 1
print(total)
"
```

The decisive Strong test sends the **same** request twice and asserts the gateway was
charged **once** (`charge.call_count == 1`). Asserting only that `AuditLogger.log` was called
is **Weak** — it proves a record was written, not that the second charge was blocked.

## 6. Golden matrix (illustrative)

| Behavior → Expected Outcome | Control (strength) | Quality cue | Status |
| --- | --- | --- | --- |
| double charge → same request bills once | `IdempotencyKey` (Preventive) | replay test asserts `call_count==1` = Strong | 🟢 if ≥2 Strong |
| plan-limit bypass → (limit+1)-th rejected | quota pre-check (Preventive) | asserts `QuotaExceeded` raised = Strong | 🟢 |
| double charge | `IdempotencyKey` | only `logger.called` asserted = Weak | 🔴 Weak Test |
| webhook replay → processed once | *(only an audit log)* — no dedup table | detect-after only | 🟡 Structural Weakness |
| free-trial abuse → 2nd trial blocked | *(unlisted)* | absent from billing spec | new candidate (Step 5) |
