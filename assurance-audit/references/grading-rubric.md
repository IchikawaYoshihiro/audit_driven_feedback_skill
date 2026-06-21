# Grading rubric — the single source of truth

This file holds the **actual scoring tables** for assurance-audit: Control strength,
Test quality, and Status. `SKILL.md` and every domain pack reference *this* file rather
than restating the tables. If two places carried the rubric, the two would drift and
no audit result could be trusted — so the tables live here, once.

> If you change a table here, re-run the self-application check (trading pack against
> its golden matrix) — a rubric edit can silently flip colors.

---

## 1. Control strength — three levels, never binary

A control is not "present / absent". The question is *what it does when the bad thing
is about to happen*.

| Strength | Meaning | Recognise it by | Examples (cross-domain) |
| --- | --- | --- | --- |
| **None** | No mechanism guards this behavior at all | nothing blocks it and nothing notices it | — |
| **Detective** | Notices the failure **after** it happens (monitor, alert, audit log, liveness check) | runs *after* the action; raises/logs/notifies but does not stop it | liveness monitor, audit log, error alert, anomaly job |
| **Preventive** | **Stops** the failure before it commits (a guard on the write/dispatch/commit path) | runs *before* the action; rejects/blocks/throws so the bad state never exists | RiskGate reject, `RateLimiter` 429, `UniqueConstraint`, `IdempotencyKey`, authz guard → 403 |

Decision: does the mechanism run **before** the dangerous action and **prevent** it
(Preventive), or **after** and merely **observe** it (Detective)? "It logs the problem"
is Detective, full stop — logging is not prevention.

---

## 2. Test quality — Strong vs Weak

For each control you find tests for, you must read the tests and grade them. A test
that *exists* is not the same as a test that *protects*. Count is necessary; quality
overrides it.

| Verdict | Condition | Example |
| --- | --- | --- |
| **Strong** | Directly asserts the **Expected Outcome** — the behavior you actually want to avoid/guarantee | asserts `fetch_cash_balance` is called; asserts `response.status == 403`; asserts a duplicate request bills exactly once |
| **Weak** | Asserts only a **side effect / related action**, not the outcome itself | asserts "processing continues" instead of asserting the aggregate notification body |
| **Weak** | **Hides the subject under a mock/stub** (always this verdict when the original incident was "the test never exercised the real thing") | `runner = AsyncMock()`; `mock_permission_checker.called` instead of a real 403 |
| **Weak** | Covers it only **indirectly** (through an adjacent feature; never exercises this behavior directly) | a happy-path test that touches the code but never the guard branch |

**Any one** of the Weak conditions makes it Weak — you do not need all of them, and you
do not need to satisfy every Strong sub-condition. If you can point at a line that
directly asserts the Expected Outcome, it is Strong. **Weak overrides Count**: ten weak
tests are still 🔴.

---

## 3. Status — health only (keep Criticality separate)

Combine Control × Count × Quality into one Status color. **Status is health, not impact.**
A "double order (None)" and a "log line missing (None)" are *both* 🔴; you decide what to
fix *first* with Criticality, which never changes the color.

| Condition | Status |
| --- | --- |
| Control = **None** | 🔴 **Missing Control** |
| Control present / Test = 0, but the ledger claims it is mitigated | 🔴 **Stale Control** |
| Control present / Test ≥ 1 / Quality = **Weak** | 🔴 **Weak Test** |
| **Expected Control = Preventive ∧ Actual Control = Detective** (prevention is achievable but the system only detects after the fact) | 🟡 **Structural Weakness** |
| Control present / Test = 1 / Strong | 🟡 **SPOF** (single point of failure — the lone test breaks → silent regression) |
| Control present / Test ≥ 2 / Strong | 🟢 **OK** |

Notes:

- **Structural Weakness** is *not* gated on Criticality. The old framing ("High + Detective
  only") was too narrow. The real signal is the **gap between the achievable and the
  actual**: if a Preventive guard *could* exist for this behavior but only a Detective one
  does, flag 🟡 — regardless of how many tests the Detective control has. (Criticality only
  decides whether you act on it now or later.)
- **Stale Control** is the false-claim case: the inventory/docs say "fixed" but there is no
  test that would fail on regression. Before declaring it, follow the anti-false-positive
  rule below — the most common cause of a wrong Stale verdict is a tag-only search.

---

## 4. The anti-false-positive rule (applies to Control *and* Test discovery)

**`grep` returning 0 ≠ "it doesn't exist".** This rule has caught real mistakes in both
directions and is non-negotiable:

- A tag/class-name search returning 0 is a *trigger to drill deeper*, never a conclusion.
- Re-search by the **Expected Outcome / behavior string** and by the **control's concrete
  identifier** (class name, reason string, log key), not just by the ledger tag.
- Count at **function granularity**, not file granularity — one giant test file can hit a
  search while only a single function actually exercises the behavior.

Two canonical misses this rule prevents (from the trading domain, see
[packs/trading.md](packs/trading.md)):

- Searching `R-15` for tests returned **0** → a tag-only audit called it 🔴 Stale Control.
  Searching the *control class* `CashLossBudgetRule` found **34** test functions → it is 🟢.
- Searching `duplicate` for the double-order guard returned nothing → suspected Missing
  Control. The behavior-based tests assert `reason == "already_holding"` directly; the
  guard (`AlreadyHoldingRule`) is wired and 🟢.
