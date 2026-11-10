# E14 Player ecosystem integration

Date: 2026-11-09

## Scope

This branch publishes the productive Michi Ecosystem package into the Michi Music Player
checkout so the Player can host the Ecosystem surfaces behind one navigation owner.

Source ecosystem checkout: `c4e4fe26ed1fe94fcfb1447185293c28f41601d1`.

Published material:

- `src/michi_ecosystem/**`: 119 Python modules plus contracts and compatibility metadata.
- `src/michi/presentation/qml/ecosystem/**`: 31 QML files (17 shared/root components and
  14 route pages).
- `src/michi/integration/ecosystem_host.py`: the Player host adapter.

No incubator history, harness, fixture tree or test data is copied into the Player runtime.

## AP2 research freeze

This work does not change the Audio Phase 2 state machine. `PHASE2_STATE.json` is untouched:

- AP2-F03 through AP2-F10 remain CLOSED.
- AP2-F11 remains ACTIVE, with productive audio work paused for this publication.
- AP2-F12 through AP2-F15 remain LOCKED.

The integration adds no playback, queue, engine, DAC, DSP, library, Signal Truth, firmware
stream or Link identity authority. Those remain with their existing Player owners.

## Runtime architecture

- One `NavigationService` owns navigation. `AppRoute.ECOSYSTEM` and
  `NavigationState.ecosystem_route` select one of the 14 declared Ecosystem routes.
- `NavigationBridge` stores the route page source and the three detail-page models
  (`server`, `linkState`, `mobile`); QML never parses a route out of a label.
- `ContentHost` has exactly one `ecosystemContentLoader`. It loads the registered route asset
  only while `currentRoute === "ecosystem"` and injects detail models when the route requires one.
- `EcosystemPlayerHost` creates exactly one `EcosystemCouplingKit` and binds the seven host
  API v1 context properties: `ecosystem`, `streamFactory`, `home`, `localAccount`,
  `streamDevice`, `homeAssistant`, `ecosystemOperations`.
- The host registers all 14 route assets with the Player-owned registrar and projects the
  canonical dashboard snapshot into the `server`, `linkState` and `mobile` detail models.
  It does not create a second navigator, popup, recorder, playback controller or DSP pipeline.

## Discovery lifecycle

Discovery starts stopped. The Discovery page exposes manual `Buscar ahora` and
`Detener búsqueda` actions backed by `EcosystemOperationsBridge` and `DiscoveryControl`.
`DiscoveryRunner` owns the background lifecycle; there is no `QTimer` poll and no continuous
scan without an explicit user action. A stop request calls
`runtime.discovery_runner.stop()`.

## Packaging

`pyproject.toml` includes:

- `michi` package data for `presentation/qml/ecosystem/*.qml` and one subdirectory level.
- `michi_ecosystem` package data for Python modules, the compatibility JSON, contracts and
  the package-local `qml/ecosystem` tree.

The built wheel contains 31 Player ecosystem QML files, 31 package QML files, the 14 route
pages, the compatibility JSON and the contract assets.

## Verification

- Navigation, bridge and integration batch: 23 passed.
- Navigation, production composition and golden-container batch: 70 passed.
- QML runtime gate after lazy loading: 16 passed (the gate no longer instantiates the
  Ecosystem page before its route is selected).
- Full local checkout suite: 7082 passed, 40 skipped. One order-dependent DSD reconfiguration
  test failed only in the full run and passed 3/3 in isolation; it does not touch this integration.
- `pyside6-qmllint` over the Ecosystem QML tree: exit 0, no `Error:` lines.
- Real bootstrap smoke: the host constructs, registers 14 routes, discovery starts stopped,
  `ecosystemContentLoader` loads `EcosystemPage` when `ecosystem` is selected and hides it
  when another route is selected.
- Wheel build and content inspection: successful; exact-SHA CI remains the release gate.

## Certification separation

- `integration_code`: implemented on `main` after merge `d2385fe`.
- `certification_software`: the full checkout suite passed before the final small
  UX/lifecycle fixes; the exact-SHA CI on the corrective HEAD is the release gate.
- `certification_physical`: NOT_RUN. No ecosystem hardware, Home Assistant broker,
  micro-server or multi-device network was exercised.
- `ap2_freeze`: preserved; no Audio Phase 2 phase-state change.

## Rollback

E14 was integrated with merge commit `d2385fe`. `git revert -m 1 d2385fe` removes the
package, QML tree, host and navigation wiring without touching audio services or phase
state. The source branch is retained only for provenance.

## QML mirror and startup weight (M11)

The canonical, tested Ecosystem QML lives in
`src/michi/presentation/qml/ecosystem/`. The independent package copy at
`src/michi_ecosystem/qml/ecosystem/` is kept only for standalone package
compatibility. `scripts/verify_ecosystem_qml_mirror.py` compares all 31 files by
SHA-256; CI fails on missing, extra or divergent files. `--sync` copies the
canonical Player tree into the package mirror when a reviewed change is ready.

The Ecosystem pages use only the Player's canonical controls, primitives,
layout and theme; they contain no NowPlayingBar, playback bridge, queue bridge,
audio engine or media player. Ecosystem buttons that have no host destination
are disabled with an explanation instead of remaining silent no-ops.

Startup flashing weight is already deferred: `EsptoolBackend` calls the esptool
CLI through `subprocess` and never imports the esptool Python package; the
serial scanner is constructed without opening a port, and no scan starts until
the user presses `Buscar ahora`. Home cryptography, Argon2id and contract
validation load because the host must create a safe Home/Registry runtime, not
because of the flashing wizard.


## Corrective hardening after the E14 merge

The mainline corrective pass keeps the same authority boundaries and adds:

- Symmetric, bounded Home backup read/write contracts (plaintext, ciphertext,
  envelope, file and entry limits) and permission-preserving atomic export.
- Coordinated `quiescing -> cancel -> wait -> close` shutdown while the Qt
  dispatcher is still available; no force-dependent invariant break.
- Exact `canonical_id` device selection for Mobile and Micro Server detail
  models, with invalidation when the selected device leaves the registry.
- Mobile diagnostics/open-in-Devices disabled with explanation where no Player
  destination exists; Home revoke routed through `HomeBridge` and OWNER
  authorization, without claiming AirCat equivalence.
- Factory flashing failures return to the review step with preserved inputs,
  visible error text and a safe explicit retry.
- Packaged Micro/Link contract bundle validation, with safe degradation when
  the bundle is absent or incompatible.
- Manual discovery with a bounded session deadline, real searching/expired/
  error/stopped states and a non-blocking stop path.
- Verified, reversible migration from incubator XDG Home/account paths into
  the Player's Ecosystem state root; existing targets are never overwritten.
- A CI-enforced AP2 research-freeze guard and a SHA-256 QML mirror check.
