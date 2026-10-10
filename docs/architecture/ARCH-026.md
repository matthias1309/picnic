# ARCH-026 — Finer Shelf-Stable Categories and Shadow-Free Keyword Rules

**Status:** draft
**Created:** 2026-10-10
**Traces:** REQ-026
**Verified by:** TEST-026

## Summary

ARCH-026 adds six categories to the fixed set from ARCH-024 (`grains`,
`breakfast`, `baking`, `condiments`, `canned`, `snacks`), keeps `pantry` as the
catch-all "Sonstige Trockenware", and reorders `CATEGORY_RULES` so that every
shelf-stable product reaches its specific category.

The change is almost entirely data: the `CategoryKey` enum, the label map, the
ordered rule tuple, and the frontend's key union plus colour map. No schema
change, no new endpoint, no new service function. The existing `apply_rules`
backfill already re-categorises rule-based products whose category changes.

The second half of the design is a structural guard: two invariant tests over
`CATEGORY_RULES` (no rule shadowed by an earlier one, no duplicate keyword)
that turn the class of ordering bug found while writing REQ-026 into a failing
test instead of a silent misclassification.

---

## Design

### Touched Components

```
backend/services/category_service.py
  CategoryKey          + GRAINS, BREAKFAST, BAKING, CONDIMENTS, CANNED, SNACKS
  CATEGORY_LABELS      + 6 labels; PANTRY → "Sonstige Trockenware"
  CATEGORY_RULES       reordered + extended (see below), duplicates removed
  categorize()         keyword is casefolded too ("ß" → "ss", found by TC-026-11)
  apply_rules()        unchanged
backend/scripts/categorize_products.py   unchanged — re-run after deploy

frontend/src/types/index.ts       CategoryKey union + 6 keys
frontend/src/lib/chart-theme.ts   CATEGORY_COLORS + 6 colours
                                  (Record<CategoryKey | "uncategorized", string>
                                   makes a missing colour a compile error)
```

Every other consumer — `GET /api/categories`, the `category` query filter
(validated against `CategoryKey`), `GET /api/stats/by-category`, the
"Artikel" dropdown and the category chart — reads the enum or the API and
picks up the new keys without code changes (AC-026-01, AC-026-06).

### Category Set

| `CategoryKey` | value | Label |
|---|---|---|
| `GRAINS` | `grains` | Nudeln, Reis & Getreide |
| `BREAKFAST` | `breakfast` | Frühstück & Aufstriche |
| `BAKING` | `baking` | Backzutaten |
| `CONDIMENTS` | `condiments` | Gewürze, Öle & Saucen |
| `CANNED` | `canned` | Konserven |
| `SNACKS` | `snacks` | Snacks & Nüsse |
| `PANTRY` | `pantry` | Sonstige Trockenware *(relabelled)* |

The enum members are inserted next to `PANTRY` so that `GET /api/categories`
lists related categories together; order is presentational only.

### Rule Order

`categorize()` stays "first keyword contained in the name wins". The new order
of `CATEGORY_RULES`, top to bottom:

```
1. False friends & compounds   ← extended (see table below)
2. Ready meals
3. Fruit
4. Vegetables                  + "grüne bohnen"
5. Dairy
6. Bakery
7. Meat
8. Fish                        + "sardine"
9. Beverages                   + "kakao"
10. Sweets                     − "chips" (moves to snacks, via block 1)
11. Breakfast   ┐
12. Snacks      │ shelf-stable, most specific first:
13. Baking      │ short, collision-prone keywords
14. Grains      │ (salz, öl, reis, pfeffer) sit in
15. Canned      │ the last two blocks, after every
16. Condiments  ┘ longer keyword that contains them
17. Personal care
18. Household
19. Frozen (storage form, last — ARCH-024 Key Decision 3)
```

Block 1 grows by every keyword whose name starts with or contains a keyword
from a fresh-food block that sits earlier:

| Keyword | Category | Would otherwise hit |
|---|---|---|
| `zahnpasta` | personal_care | `pasta` |
| `wassereis` | sweets | `wasser` (beverages) |
| `nektarine` | fruit | `nektar` (beverages) |
| `preiselbeer` | breakfast | `reis` |
| `reiswaffel` | snacks | `waffel` (sweets) |
| `kichererbsen` | grains | `erbsen` (vegetables) |
| `chips` | snacks | `paprika` (vegetables) in "Paprika Chips" |
| `ketchup` | condiments | `tomate` in "Tomatenketchup" |
| `tomatenmark` | condiments | `tomate` |
| `passierte tomaten`, `gehackte tomaten` | canned | `tomate` |
| `brühe` | condiments | `gemüse`, `rind` |
| `essig` | condiments | `apfel` in "Apfelessig" |
| `backkakao` | baking | `kakao` (beverages) |
| `kokosmilch` | canned *(was pantry)* | `milch` |
| `erdnussbutter` | breakfast *(was pantry)* | `butter` |
| `marmelade`, `konfitüre` | breakfast *(was pantry)* | fruit keywords |

The keywords per shelf-stable block are those listed in REQ-026 Notes; the
exact final list lives in code and is pinned by the TEST-SPEC examples.

### Invariant Tests (AC-026-08)

Two tests run over the whole rule tuple, not over hand-picked examples:

```python
for keyword, category in CATEGORY_RULES:
    assert categorize(keyword) == category      # nothing earlier shadows it

keywords = [keyword for keyword, _ in CATEGORY_RULES]
assert len(keywords) == len(set(keywords))      # no dead duplicates
```

Run against today's rules, the first test fails for exactly the four defects
listed in REQ-026 (`nektarine`, `wassereis`, `zahnpasta`,
`passierte tomaten`); the second for `saft`, `joghurt`, `quark`, `skyr`,
`marmelade`. Both must pass after the change.

The shadowing test cannot see multi-word names whose *combination* collides
(e.g. "Apfelessig": neither `apfel` nor `essig` shadows the other). Those are
covered by the example tables in AC-026-02/03.

### Data Transition

No schema change and no migration. After deploy (and the Gunicorn restart, see
learnings 2026-06-16) the existing backfill is re-run:

```bash
python -m backend.scripts.categorize_products
```

`apply_rules` only touches non-manual products and only writes when
`categorize()` returns a category that differs from the stored one, so:

- rule-based `pantry` products move to their new category (AC-026-05);
- manually assigned `pantry` products are untouched (AC-026-04);
- a rule-based product no new rule matches keeps its old category — never
  reset to "Nicht zugeordnet";
- a second run reports 0 changes.

### Frontend Colours

Six new entries in `CATEGORY_COLORS`. They must be distinguishable from the
existing 14 in light and dark mode; in particular `snacks` must differ from
`sweets`, and the shelf-stable family from `bakery` and `pantry`. Chosen with
the dataviz palette method and checked with its validator during
implementation (AC-026-07).

---

## Key Decisions

### 1. Flat sibling categories, not sub-categories

REQ-024 rules out sub-categories ("exactly one category per product"). Six flat
keys reuse every existing endpoint, filter and chart as-is. A two-level
hierarchy would need a parent field, a grouped chart and a grouped filter — a
REQ of its own for one split.

### 2. Keep `pantry` as a catch-all instead of removing it

Removing the key would orphan manual assignments (the column holds a free
string) and need a data migration that guesses a new category for products
a human chose deliberately. Keeping it costs one relabel and lets the user
re-sort manual assignments at leisure in the article list.

### 3. Shortest keywords last, guarded by a generic test

Ordering by "specific before general" is the established rule (ARCH-024 Key
Decision 3), but it has been violated four times without anyone noticing,
because tests only checked chosen examples. A property over all rules is
cheap, has no false positives on today's intended order, and catches every
future addition that would be dead on arrival.

### 4. No change to `categorize()` matching (still substring)

Word-boundary or token matching would fix some collisions (`öl` in "Kölln")
but break the German compound nouns the rules rely on (`milch` in
"Vollmilch", `mehl` in "Weizenmehl"). Substring matching plus ordering stays
the simpler, already-tested model.

---

## Out of Scope

- AI-based category suggestions (separate topic, would need its own REQ).
- Re-assigning existing manual `pantry` products — that is a user action in
  the article list.
- Splitting other broad categories (`household`, `beverages`).
- Changing the matching algorithm (Key Decision 4).

## Open Questions

- None blocking. Borderline products ("Schoko Müsli" → sweets because `schoko`
  comes first; "Hefezopf" → baking via `hefe`) are accepted and correctable by
  hand; they are not added as exceptions unless they show up in real receipts.
