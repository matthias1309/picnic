# ARCH-027 — Keyword Rule Gaps from the Live Database Review

**Status:** draft
**Created:** 2026-10-10
**Traces:** REQ-027
**Verified by:** TEST-027

## Summary

Data-only change to `CATEGORY_RULES` in `backend/services/category_service.py`:
new keywords, three keywords moved earlier, and one keyword replaced. The matching
algorithm (`categorize()`: casefolded substring, first match wins), the schema,
the API and the frontend stay as they are. The invariant tests TC-026-11
(no shadowed rule) and TC-026-12 (no duplicate keyword) must stay green.

## Decisions per Review Row

"Top" is the false-friend and compound block at the start of `CATEGORY_RULES`.

| Product | Was | Decision |
|---|---|---|
| Tomaten stückig / Stückige Tomaten | vegetables | Top: `tomaten stückig`, `stückige tomaten` → canned |
| Tomaten passiert | vegetables | Top: `passiert` → canned. It replaces `passierte tomaten`, which it contains, so keeping both would leave a dead rule |
| Getrocknete Tomaten in Öl | vegetables | Top: `getrocknete tomaten` → canned |
| Grüne Oliven … | vegetables | Top: `oliven` → canned, preceded by `olivenöl` → condiments (see Olive Ordering) |
| Gewürzgurken, Sandwich Gurken, Cornichons | vegetables / none | Top: `gewürzgurke`, `sandwich gurken`, `cornichon` → canned. Plain `gurke` stays vegetables so "Salatgurke" is unchanged. `essiggurke` → canned precedes `essig` |
| Mandeln gehackt | meat (`hack`) | Top: `mandeln gehackt`, `gehackte mandeln` → snacks. A narrow pair, not a move of `mandeln`, so "Schoko Mandeln" stays sweets |
| Meßmer / Teekanne | fruit | `tee` moves to Top (→ beverages) so "Apfeltee" wins over `apfel`; `teewurst` → meat precedes it. `meßmer` → beverages: the name has no generic tea word, and Meßmer sells only tea |
| Mini Pflaumen Tomaten | fruit (`pflaume`) | Top: `pflaumentomate`, `pflaumen tomaten` → vegetables |
| Spezial-Salz | condiments | Top: `spezial-salz`, `spezial salz` → household (dishwasher salt) |
| Essigspray | condiments | Top: `essigspray` → household. `essigreiniger` → household is added as well; it has the same defect (`essig` beats `reiniger`) |
| Taschentücher | none | Personal care: `taschentuch` is replaced by `taschentü`, which matches both "Taschentuch" and "Taschentücher" |
| Purina cat food | fish (`lachs`) | Top: `tierfutter`, `katzenfutter`, `hundefutter` → other, plus the brand `purina`: the product name contains no generic pet-food word. Not `futter`, which would catch "Studentenfutter" |
| Tortelloni | none / mixed | Ready meals: `tortelloni`. Tortellini and Ravioli are not added until they appear on a receipt |
| Butter-Chicken | dairy (`butter`) | Top: `butter-chicken`, `butter chicken` → meat. `hähnchen` is not moved, because that would reorder it against ready meals and dairy for all chicken products |
| Paprika edelsüß | vegetables | Top: `edelsüß`, `paprikapulver` → condiments |
| Röstzwiebeln | vegetables | Top: `röstzwiebel` → condiments |
| Chocolate Chunks | beverages (`cola` in "chocolate") | Top: `chocolate chunks` → baking, followed by `chocolate` → sweets, which fixes the `cola` match for every English "chocolate" name |
| Cup Noodles | none | Ready meals: `cup noodles`. Plain `noodles` is not used because it would also catch rice noodles |
| Rohrfrei | none | Top: `rohrfrei` → household. It cannot sit in the household block: dairy's `ei ` matches "Rohrfrei Power" |
| E-Block | none | Household block, last: `e-block`. In Top it would take "Käse-Block"; in the household block any food rule fires first |
| Porree | none | Vegetables: `porree`, next to `lauch` |

### Olive Ordering

`oliven` is contained in `olivenöl`, and `olivenöl` must stay condiments. So
`olivenöl` precedes `oliven`. That would move "Sardinen in Olivenöl" from fish to
condiments, because the fish block comes after Top. Therefore `sardine` and
`thunfisch` move from the fish block to Top, ahead of `olivenöl`. Fish canned in
oil is a fish product (AC-027-05). `makrele` and `hering` stay put: "in Olivenöl"
variants are rare, and a moved keyword is a behaviour change.

### Behaviour Changes Beyond the Table

- `tee` moves before the fruit and dairy blocks: "Apfeltee" and "Milchtee" are
  now beverages.
- `sardine` and `thunfisch` move before the vegetable block: "Thunfisch Salat"
  is now fish instead of vegetables.
- `chocolate` → sweets: English "Chocolate …" names no longer hit `cola`.

All three are corrections. They are accepted and listed here so the next
reviewer finds them.

## Constraints Respected

- Shadow invariant: each new keyword is checked alone with `categorize()`, so
  the pairs above are ordered longest-first (`olivenöl` before `oliven`,
  `teewurst` before `tee`, `chocolate chunks` before `chocolate`, `essiggurke`,
  `essigspray` and `essigreiniger` before `essig`).
- No duplicates: `sardine`, `thunfisch` and `tee` are moved, not copied.
- Short, collision-prone keywords stay at the end of their blocks
  (ARCH-026 ordering constraint 3).

## Out of Scope

- The live database and production. The account owner backfills by hand.
- Changing `categorize()` matching (ARCH-026 Key Decision 4).
- Tortellini, Ravioli and other fresh filled pasta; noodle soups other than
  Cup Noodles.
