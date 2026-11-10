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

- `integration_code`: implemented on the integration branch.
- `certification_software`: pending the full checkout suite and exact-SHA CI.
- `certification_physical`: NOT_RUN. No ecosystem hardware, Home Assistant broker,
  micro-server or multi-device network was exercised.
- `ap2_freeze`: preserved; no Audio Phase 2 phase-state change.

## Rollback

The integration is isolated on `e14/ecosystem-integration-20261109`. Reverting the branch
commit removes the package, QML tree, host and navigation wiring without touching audio
services or phase state.
