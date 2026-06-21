# Domain pack — web service / backend API (security)

Maps a web application's security-relevant behaviors onto the generic engine. The same
`Inventory → Threat Discovery → Control → Test → Quality → Status` flow applies; only the
vocabulary and recipes below are domain-specific.

---

## 0. Inventory location (Step -1)

Where the ledger of protected behaviors lives:

- **Primary**: a threat model / security requirements doc / ADRs covering auth & data
  access. Many web projects have **none** — that absence is the top-priority Gap.
- **Secondary**: security-incident postmortems, an OWASP/ASVS checklist if adopted, the
  issue tracker's `security` label.
- **Fallback taxonomy** if no ledger exists: §2.

## 1. Ledger source & enumeration (Step 0)

If a threat model exists, enumerate its entries. Otherwise derive Protected Behaviors from
the route/endpoint table cross-referenced with §2 (every state-changing or data-returning
route implies at least an authz behavior). Give each an Expected Outcome, e.g.:

- authz on `/admin/*` → *a non-admin session gets 403, never 200*
- account registration → *a second signup with the same email is rejected*

## 2. Standard taxonomy (Step -0.5 yardstick + Step 1 categories)

The forgotten ones (marked ⚠) are exactly what Threat Discovery should surface:

- **AuthZ / access**: missing authorization on a route / IDOR (object belongs to another
  user) / ⚠ privilege escalation via mass-assignment
- **AuthN / session**: ⚠ password-reset token reuse or non-expiry / ⚠ session fixation /
  brute-force on login
- **Input / injection**: SQL/command injection / stored XSS / SSRF on user-supplied URLs
- **Rate / abuse**: ⚠ email/SMS-resend spam / ⚠ enumeration via timing or 404-vs-403 /
  unthrottled expensive endpoints
- **Data exposure**: over-broad serializer leaking fields / ⚠ verbose errors leaking stack
  traces or internal IDs

## 3. Criticality rubric (Step 4, ordering only)

**High** = anything touching authentication, authorization, or PII/financial data.
Med = abuse/DoS-class. Low = informational leaks with no direct escalation. Ordering only.

## 4. Preventive vs Detective in this domain

| Behavior | Preventive (blocks before commit) | Detective (notices after) |
| --- | --- | --- |
| authz bypass | policy gate / middleware returning **403** before the handler | access-log anomaly alert |
| duplicate registration | DB `UNIQUE` constraint / pre-insert check | dedup batch job |
| IDOR | ownership check on the queried object before returning it | audit log of cross-tenant reads |
| rate abuse | `RateLimiter` returning **429** | spike alert on request volume |
| password-reset reuse | single-use, time-boxed token invalidated on use | alert on repeated resets |

Reminder: an audit log or alert is **Detective**. A 403/429/constraint that stops the
request is **Preventive**.

## 5. Test-discovery recipe (Step 2, function-granular)

Search by **Expected Outcome** (the status code / rejection) and by the **guard's name**,
not just a route path. Example for a pytest/Django/FastAPI stack:

```bash
python3 -c "
import re
from pathlib import Path
# Expected Outcome (403/429/unique) OR the guard identifier
rx = re.compile(r'==\s*403|status_code\s*==\s*403|429|IntegrityError|UniqueConstraint|PermissionDenied')
total = 0
for p in Path('tests').rglob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    for f in re.split(r'(?m)^\s*(?=(?:async )?def test_)', text):
        if rx.search(f): total += 1
print(total)
"
```

Adapt the regex per stack (RSpec: `have_http_status(:forbidden)`; Jest/supertest:
`.expect(403)`; Go: `httptest` + `http.StatusForbidden`).

## 6. Golden matrix (illustrative)

A worked shape (fill counts from a real repo when you adopt this pack). Note how the
Strong/Weak distinction bites here — `assert status == 403` is Strong; asserting only
`mock_permission_checker.called` is **Weak** (it proves the guard was *consulted*, not that
an attacker is actually stopped).

| Behavior → Expected Outcome | Control (strength) | Quality cue | Status |
| --- | --- | --- | --- |
| authz on admin route → non-admin gets 403 | PermissionGuard (Preventive) | `assert resp.status==403` = Strong | 🟢 if ≥2 Strong |
| duplicate registration → 2nd email rejected | `UNIQUE` constraint (Preventive) | asserts the insert raises = Strong | 🟢 |
| IDOR → other user's object → 404/403 | ownership check (Preventive) | only-happy-path test = Weak | 🔴 Weak Test |
| password-reset reuse → 2nd use rejected | *(often none)* — only a reset-sent log | no pre-use invalidation found | 🟡 Structural Weakness / 🔴 Missing |
| email-resend spam → throttled | *(often unlisted)* | absent from threat model | new candidate (Step 5) |
