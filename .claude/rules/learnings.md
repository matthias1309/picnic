# Project Learnings

This document grows with the project. New insights are captured with `/capture-learning`.
Claude reads this file every session and factors the entries into suggestions and decisions.

**Format:**
```
## YYYY-MM-DD — Short title
**Context:** When/where was this noticed?
**Learning:** What did we learn?
**Action:** What do we change or watch out for going forward?
```

---

<!-- Entries are appended here chronologically -->

## 2026-06-16 — Match Picnic style markers tolerantly, not by exact CSS substring
**Context:** A new invoice failed to parse (`No item rows found`). Picnic had
re-rendered the item-row style from `border-bottom:1px solid #ebebeb` to
`border-bottom: 1px solid #EBEBEB` (extra space, uppercase hex). The exact,
case-sensitive `td[style*="..."]` selector matched zero rows. The same email
also nests `Gesamtbetrag` differently, which silently broke total reconciliation.
**Learning:** Picnic's HTML template varies whitespace/case and nesting between
versions. Exact string/selector matching against their styles is brittle, and a
single format tweak can zero out a whole receipt. Non-product rows (Pfand,
Lieferadresse) can also share the item-row border style.
**Action:** Compare style markers via a normalized form (lowercase, spaces
stripped) and require a product `img[alt]` to qualify a row as an item. When a
parse regression appears, diff the new email's markup against a known-good
fixture first. Total reconciliation for the current `Gesamtbetrag` layout is a
known open follow-up (REQ-012 findings).
