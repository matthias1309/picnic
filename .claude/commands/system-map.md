Generate a horizontal system map showing how all requirements and architectures interrelate.

This complements `/traceability` (which is *vertical*: REQ → ARCH → TEST → code coverage).
`/system-map` is *horizontal*: which REQs share a scope, what builds on what, which
architecture components are touched by many features, and where the change-risk hotspots are.

The primary consumer is the **Impact Analysis** step (V-Model step 0, see `.claude/rules/v-model.md`):
this map is the pre-computed "touchpoint index" used to find the REQs related to a new story
without re-reading the whole catalog.

## How to build it

Do NOT rely on regex alone — explicit `REQ-XXX` cross-references in the files are sparse.
The real relationships live in shared modules, shared database tables, and the Background/Overview
sections. You must read and interpret, not just grep.

1. Scan `docs/requirements/REQ-*.md` (ignore `*-supersedes-*` files for the main list, but use
   their filenames to record the old FEAT lineage) and `docs/architecture/ARCH-*.md`.
2. For each REQ, extract:
   - Title and status
   - **Touchpoints** — the modules, database tables, calculations, routes, and UI surfaces it
     affects. Read the REQ Background/ACs and its ARCH (`Database Schema`, `Overview`, file lists).
   - **Explicit references** — any `REQ-XXX` mentioned in the body or the `Impact Analysis` section.
   - **Supersedes lineage** — from `REQ-XXX-supersedes-FEAT-YYY.md` filenames.
3. Derive REQ↔REQ relationships from BOTH explicit refs AND shared touchpoints
   (two REQs writing the same table, or extending the same module, are related even with no link):
   - **builds-on** — REQ depends on capability introduced by another (e.g. a tile builds on an import)
   - **overlaps** — both touch the same module/table/calculation, compatible
   - **supersedes / superseded-by** — lineage or explicit replacement
4. Stamp the output with today's date (run `date +%F`).

## Output — write to `docs/SYSTEM-MAP.md`

Use this structure:

```markdown
# System Map — Project_Buddy

**Generated:** <YYYY-MM-DD> · **Source:** N REQs, N ARCHs · **Regenerate:** `/system-map`

> ⚠️ Generated artifact. Do not hand-edit — it will be overwritten. If a relationship here
> looks wrong, fix the underlying REQ/ARCH and regenerate. Treat this map as stale once any
> REQ/ARCH changes; regenerate before relying on it for an impact analysis.

## Domain Clusters

Group every REQ under a functional domain (e.g. Auth & Access, Excel Import, Dashboard & Tiles,
Master Data, Capacity & Employees, Platform & Infra). For each cluster:

### <Domain name>
- **REQs:** REQ-XXX (Title), REQ-YYY (Title), …
- **Shared architecture:** the tables / modules / routes this cluster owns
- **One-line purpose**

## Dependency Matrix

| REQ | Title | Builds on | Overlaps with | Supersedes |
|-----|-------|-----------|---------------|------------|
| REQ-006 | Project Detail Dashboard | REQ-004, REQ-005 | REQ-011, REQ-012 | — |

(Show only non-empty relationships. "Builds on" = hard dependency; "Overlaps with" = shared touchpoint.)

## Architecture Interplay (Touchpoint Index)

For each shared module / database table / calculation, list which REQs touch it.
This is the lookup the impact analysis uses — "new story touches X → these REQs also touch X".

| Touchpoint | Type | Touched by |
|-----------|------|------------|
| `project_employees` | table | REQ-027 |
| stability-index calc | calculation | REQ-006, REQ-007, REQ-023 |
