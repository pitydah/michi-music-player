# Premium Library QML lint policy

The CI warning gate covers the six Library projections, their orchestration,
View Options, Album Detail, breakpoints, and material primitives with a zero
warning budget.

Three diagnostic classes are excluded because these QML files intentionally
consume Python context properties (`library`, `enrichment`, and settings), and
because `PathView` supplies dynamic path attributes that are not represented in
static qmltypes metadata:

- `context-properties`
- `unqualified`
- `missing-property`

All remaining diagnostics count against the zero-warning budget. Layout
positioning is explicitly elevated to an error. The full QML tree is also linted
separately as a syntax and type gate.
