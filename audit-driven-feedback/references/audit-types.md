# Audit Types — Detection Recipes

Detailed catalog for the 7 audit types. For each: what it protects, the two sides it
compares, **how to enumerate the set** (the crux — audits must walk the whole set,
not a sample), typical violations, and a language-agnostic detection sketch.

Pseudocode is intentionally stack-neutral. Map "enumerate routes / events / files /
config keys" onto whatever reflection or static-analysis the target stack offers
(framework route collections, DI container introspection, AST parsing, file globs,
DB schema queries).

## Table of contents
1. Parity
2. Wiring
3. Data
4. Docs
5. Config
6. Architecture
7. Process

---

## 1. Parity audit

**Protects:** one half of a thing that must come in pairs goes missing.

**Compares:** every member of set A has a corresponding member in set B.

**Enumerate:** list set A exhaustively from a canonical source (the framework's route
table, the generated API spec, an enum definition, a DB column's distinct values).

**Typical violations:**
- a route with no authorization/permission attached
- an HTTP endpoint absent from the OpenAPI/API spec (or spec entry with no endpoint)
- an enum case with no matching DB value, or a DB value with no enum case
- a DTO field with no validation rule

**Detection sketch:**
```
required, exempt = load_desired_state()      # canonical list + reviewed allowlist
violations = []
for item in enumerate_all(set_A):            # ALL of them, from the source of truth
    if item in exempt: continue
    if not has_counterpart(item, set_B):
        violations.append((item, "missing counterpart in B; add it or exempt it"))
fail_if(violations)
```

---

## 2. Wiring audit

**Protects:** something is built but never connected — the silent-drift archetype.

**Compares:** a producer/definition exists ⇒ its consumer/registration also exists.

**Enumerate:** discover all definitions of the producer kind (all event classes, all
notification classes, all jobs, all listeners) via reflection or file scan, then check
each is actually referenced/registered/dispatched somewhere.

**Typical violations:**
- a notification class defined but never dispatched (the "alert that never fires")
- an event with no registered listener (or a listener for a deleted event)
- a queued job class never enqueued, or enqueued onto an unconfigured queue
- a feature flag defined but never read, or read but never defined

**Detection sketch:**
```
definitions = discover_all(kind="notification|event|job")
for d in definitions:
    refs = find_references(d)                 # dispatch sites / registrations
    if refs.is_empty():
        violations.append((d, "defined but never wired; connect it or delete it"))
```
Note: "never referenced" can mean *dead code* OR *forgotten wiring*. The message
should ask the human/agent to decide which — both are real findings.

---

## 3. Data audit

**Protects:** invariants over stored state that the schema can't express.

**Compares:** the data against a rule that must always hold.

**Enumerate:** express each invariant as a query that returns the *count of
violations*; zero is healthy. Keep them cheap enough to run on production data.

**Typical violations:**
- a soft-deleted parent still has active children (deleted user ↔ active orders)
- a denormalized aggregate disagrees with its source (order.total ↔ sum of lines)
- orphaned rows (FK target gone), or status combinations that should be impossible
- monetary/`quantity` fields that should never be negative

**Detection sketch:**
```
rules = { "deleted user has active order": "SELECT COUNT(*) ... ",
          "total != sum(lines)":          "SELECT COUNT(*) ... " }
for label, query in rules:
    n = run(query)
    if n > 0: violations.append((label, f"{n} rows violate this invariant"))
```
This is the audit most worth running on a schedule against the live DB, because data
drifts even when code doesn't.

---

## 4. Docs audit

**Protects:** documentation silently going stale after refactors.

**Compares:** references inside docs ⇒ the referenced thing still exists.

**Enumerate:** scan all doc files; extract every machine-checkable reference (class
names, route names, file paths, command names, config keys) and resolve each.

**Typical violations:**
- docs mention a class/module that was renamed or deleted
- a documented route name / CLI command no longer exists
- a relative link or file path that 404s
- a documented config key not present in config

**Detection sketch:**
```
for doc in all_docs():
    for ref in extract_references(doc):       # `App\Foo`, route('x'), ./path, ...
        if not resolves(ref):
            violations.append((doc, ref, "doc references something that no longer exists"))
```
Keep extraction conservative (match a clear citation syntax) to avoid false positives
on prose. A noisy docs audit gets muted fast.

---

## 5. Config audit

**Protects:** configuration / environment divergence.

**Compares:** the set of declared config keys ⇒ the set actually used, across
environments.

**Enumerate:** read the example/template env file's keys, the loaded config keys, and
each environment's config; diff the key sets (not necessarily the values).

**Typical violations:**
- a key read by the app but absent from `.env.example` (new dev can't boot)
- a key in `.env.example` no longer read anywhere (stale, misleading)
- a key present in one environment's config but missing in another
- a secret referenced in code with no documented provisioning

**Detection sketch:**
```
declared = keys(env_example)
used      = keys_referenced_in_code()
missing_from_example = used - declared
stale_in_example     = declared - used
violations += label_each(missing_from_example, "used but undeclared")
violations += label_each(stale_in_example,     "declared but unused")
```

---

## 6. Architecture audit

**Protects:** stated layering / dependency rules that nothing enforces.

**Compares:** actual import/dependency graph ⇒ the allowed direction.

**Enumerate:** parse imports/use-statements per module; classify each module into its
layer; check every edge against the allowed-direction rule.

**Typical violations:**
- domain/core layer importing infrastructure/framework code
- a module reaching across a bounded-context boundary it shouldn't
- a UI layer touching the database directly, bypassing the service layer
- circular dependencies between packages

**Detection sketch:**
```
rules = [("domain", "must_not_import", "infra"), ...]
for module in all_modules():
    layer = classify(module)
    for dep in imports_of(module):
        if violates(layer, classify(dep), rules):
            violations.append((module, dep, "illegal dependency direction"))
```
Many ecosystems have ready tools for this (dependency linters / arch-unit style
libraries). Prefer wrapping an existing one over hand-rolling AST parsing.

---

## 7. Process audit

**Protects:** gaps in the development process itself, not the running system.

**Compares:** an artifact ⇒ the process artifact it should have.

**Enumerate:** list the primary artifacts (endpoints, public API surface, migrations,
features) and check each has its required companion (a test, a changelog line, a
rollback, an owner).

**Typical violations:**
- a controller/endpoint with no test referencing it at all
- a public API change with no changelog/migration-notes entry
- a DB migration with no down/rollback path
- a module with no declared owner (CODEOWNERS gap)

**Detection sketch:**
```
for artifact in primary_artifacts():
    if not has_companion(artifact, kind="test|changelog|rollback|owner"):
        violations.append((artifact, "missing required process artifact"))
```
Process audits are easy to over-apply and turn into nagging. Apply them only where a
missing companion has actually hurt before (the Prioritize step in SKILL.md). "Every endpoint must
have a test" is reasonable; "every function must have a docstring" is usually noise.
