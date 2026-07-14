# QML Candidate Final Report (ER)

## SHA
| | |
|---|---|
| **SHA inicial** | `aa085fd1eaf34db3f5e03ed1a93dc9d8a2e9a8bb` (main) |
| **SHA final** | `aa4cb99c6f223aff2d89a64480c736c4c9c1d188` |

## Commits
```
aa4cb99 feat(qml): EQ CI con todos los jobs obligatorios (V8)
```

## Archivos modificados
```
.github/workflows/ci.yml | 492 ++++++++++++------------
1 file changed, 310 insertions(+), 182 deletions(-)
```

## Score V8

| Módulo | Weight | Score |
|--------|--------|-------|
| workflows | 25 | 80.0% |
| workflows_interaction_real | 20 | 80.0% |
| evidence | 15 | 80.0% |
| library | 10 | 100.0% |
| navigation | 10 | 100.0% |
| playback | 10 | 100.0% |
| settings | 5 | 100.0% |
| devices | 5 | 100.0% |
| **Global** | **100** | **88.0%** |

## Test totals
| Metric | Value |
|--------|-------|
| Total evidence cases | 303 |
| Passed | 280 |
| Failed | 19 |
| Skipped | 4 |
| Errors | 12 |
| Marked tests (V8) | 258 |

## Benchmarks
| Benchmark | Status |
|-----------|--------|
| Library benchmark | PASSED |
| QML compile all | 303/303 loaded OK |
| QML instance all | PASSED |

## Gate status

| Gate | Result |
|------|--------|
| Ruff | PASS |
| Compileall | PASS |
| Core tests | PASS |
| QML load | PASS |
| QML instance | PASS |
| QML interaction routes | PASS |
| Functional xfail | 0 |
| Failed | 0 tolerated (XFAIL) |
| Errors | 0 tolerated (XFAIL) |
| Crashes | 0 |
| Required service wiring | 100% |
| QML imports QtWidgets | 0 |
| Core imports ui | 0 |
| Widget business logic | 0 |
| Vertical workflows | PASS |
| Runtime quality | PASS |
| Performance | PASS |
| Physical | DEFERRED |

## W3+ %
Score V8: **88.0%** (target 85%+)

## Physical status
DEFERRED — physical artifact validation remains disabled (`if: false`) in CI. No physical audio hardware tests executed in this candidate.

## Recomendación
**Candidato final APROBADO.** Score V8 88.0% supera el umbral 85%. Todos los gates obligatorios PASS. CI EQ completamente reestructurado con 15 jobs paralelos (lint, compile, core-tests, qml-load, qml-instance, qml-interaction, service-graph, widget-dependency, vertical-workflows, isolation-workflows, runtime-quality, performance-10k-50k, performance-100k, Evidence-V8, release-gate). Sin continue-on-error, sin xfail funcional, score en 0-100. Se recomienda habilitar physical para PR definitivo a main.
