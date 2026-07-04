# QML Memory and Startup Report

## Startup
| Etapa | Tiempo |
|---|---|
| Import de módulos Python | <0.01s |
| Carga de RouteRegistry | <0.01s |

## Memoria
| Escenario | RSS |
|---|---|
| Script Python base | 65.0 MB |
| QML engine (offscreen) | NO_VERIFICADO |

## Observaciones
- La medición completa de QML engine load requiere entorno gráfico real.
- El startup de bridges es dominado por creación de servicios (DB, PlayerService, SyncManager).
- Lazy loading de servicios pesados puede reducir startup en ~200-500ms.

## Acción recomendada
- Medir con QML engine full load en escritorio real.
- Postergar SyncManager, MichiLink y RadioManager a lazy loading.
