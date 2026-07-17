# QML UI/UX Refinement V2 — Progress

## Branch
`feature/qml-uiux-refinement-v2`

## Commits

| # | Commit | SHA | Files | Δ |
|---|--------|-----|-------|---|
| 1 | style(qml): finalize Michi branding and icon system | 22c6c397 | 2 | +722/-260 |
| 2 | style(qml): refine responsive application shell | dae75cda | 5 | +153423/-94 |
| 3 | style(qml): consolidate now playing experience | f9a978f8 | 4 | +19/-62 |
| 4 | style(qml): refine minimal home dashboard | 84a8e914 | 5 | +13/-17 |
| 5 | style(qml): improve library navigation and density | 7a3a71e0 | 7 | +8/-8 |
| 6 | style(qml): unify album view visual language | 37bc92ce | 5 | +24/-30 |
| 7 | fix(qml): replace remaining hardcoded radius and sizes | a6187ef8 | 8 | +10/-10 |
| 8 | a11y(qml): close priority accessibility and focus gaps | 25808a6f | 1 | +1/-0 |

## Fulfilled objectives

- [x] F0: Baseline + branch created
- [x] F1: Branding — no "MP" letters, app_icon.svg, no "Experimental" badge
- [x] F2: Routes nowplaying/jobs registered, DiscLab states, ToastHost/SettingsRow tokens
- [x] F3: NowPlaying controls unified with MichiIconButton
- [x] F4: Home cards density + sizing
- [x] F5: Library density tokens
- [x] F6: Album view selector with icons, CoverFlow tokens
- [x] F7-13: Token cleanup across 8+ files
- [x] F14-15: Accessibility (Escape on NotificationCenter), perf (no blur)

## Pending for gate
- [ ] F16: Test suite verification
- [ ] F17: Final report
- [ ] F18: Gate (ruff, compileall, smoke) + push
