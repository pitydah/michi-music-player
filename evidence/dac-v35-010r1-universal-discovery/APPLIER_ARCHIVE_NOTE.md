# Archived one-shot corrective applier

`apply_michi_dac_universal_corrective.py` preserves the historical, fail-closed
applicator that produced the M11.4 universal audio discovery corrective on top of
`e0eb9fc3df4648bb3d6341341427f16b800be2f2` (it verifies the Git blob SHA of every
file it edits before touching it).

The archived payload is **audit evidence, not an executable from this path**.
It was authored while living under `scripts/`, where
`Path(__file__).resolve().parents[1]` resolved to the repository root. After the
byte-preserving relocation under `evidence/dac-v35-010r1-universal-discovery/`,
that same expression resolves to `evidence/`. Do not edit the captured payload
to make a historical applicator look current; the committed Git diff/history is
the reproduction authority for the resulting product state.

It is archived here instead of `scripts/` because:

- its own contract is to delete itself after a successful `--apply` (the applied
  diff is already what the repository contains);
- it embeds the full payload of every new/edited file as string literals, so all
  142 of its `E501` findings live inside those literals. Reformatting it for the
  `ruff` gates would change the embedded payload, i.e. it would stop being an
  exact record of what was applied.

It is audit material, not product or test code, and is intentionally outside the
`ruff` scope (`src tests scripts`).
