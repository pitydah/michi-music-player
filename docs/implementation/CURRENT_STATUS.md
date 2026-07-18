# Current Status

## Post-segunda ola completa
**Commit:** 89ace63d
**Branch:** main (QML-only)
**Arranque:** 0.52s
**RAM:** 16MB
**Wheel:** 2.2MB
**Tests:** 304 funcionales + ~2970 core

### Completado
- [x] QML-only: 0 QtWidgets imports
- [x] Composition root separado (8 builders)
- [x] Modelos tipados (TrackRef, OperationResult)
- [x] 54 settings adapters
- [x] Secrets redactados
- [x] FakePlayer backend
- [x] Sidebar rediseñado
- [x] HomePage música primero
- [x] E2E listen flow (scan→search→queue→session)
- [x] i18n: 2145 strings con qsTr en 311 QML files
- [x] MixRuleEngine (AND/OR, seed, preview)
- [x] saveRules/previewRules en MixBridge
- [x] Lyrics: sidecar .lrc, offset, editing, cache
- [x] Metadata rename engine (templates, preview, security)
- [x] Library Doctor scan con biblioteca dañada
- [x] EQ state sync + output profiles
- [x] Radio avanzada (repository, search, history)
- [x] Audio Lab batch processing
- [x] CD Ripper command building + detection
- [x] Portable Player Sync (UMS, transcode, registry)
- [x] Mobile Sync (pairing, QR, trust, protocol)
- [x] Micro Server integration (discovery, client)
- [x] Home Audio (Snapcast, HA adapter, handoff)
- [x] Michi AI (intents, security, action validation)
- [x] Job Center UI + DurableJobService
- [x] Performance baseline
- [x] Accessibility tests (10)
- [x] Bridge contract validation (CI gate)

### Pendiente
- 49 tests fallando (preexistentes, no introducidos por segunda ola)
- F11 (CD/ADC) requiere hardware para validación completa
- F15 (Mobile Sync) requiere cliente móvil real
