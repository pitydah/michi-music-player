# Michi Music Player — AP2-F11 Signal Truth
## A44/D20: contrato de handoff, inventario de pruebas y reglas de recepción

**Paquete:** un único parche acumulativo A44 + un único plan maestro A00–A44 en Google Drive.
**Estado del kit:** ingeniería preparada; validación del checkout productivo, Qt/KWin, DAC y CI pendientes.
**Prohibición:** ninguna operación de GitHub remota, creación de commit, branch o PR forma parte de este kit.
**Propietarios:** `SignalTruthRecorder` único, proyección F03, `TruthFrame` A42, bridge Qt único.
**Límite normativo:** AGENTS.md, R11-F11, AP2 Bible, DAC V3.5, `PHASE2_STATE.json` prevalecen. Un desacuerdo no se resuelve reescribiendo documentos.

### 1. Matriz obligatoria del recibo A44

Los 18 gates son independientes. `PASS` requiere un archivo de evidencia acotado con hash SHA-256, `run_id`, resultado de proceso `exit_code=0` y frontera explícita. Los campos de un recibo son **declaraciones del operador**, no sustituyen una auditoría del contenido de los archivos.

| Grupo | Gates | Observación de aceptación |
|---|---|---|
| Canon | `canonical_context`, `ap2_alignment`, `dac_alignment` | verificadores reales y ausencia de contradicción vigente |
| Package | `patch_integrity`, `post_migration_tree`, `python_regressions`, `rollback_drill` | diff único A44, hash fijo; espejo posmigración; sin cambios no autorizados |
| UI | `qt_owner_dispatch`, `qml_truth_frame`, `kwin_a11y_dpr` | pruebas reales PySide6/QML/KWin, owner thread, teardown, DPR/foco |
| Operación | `privacy_redaction`, `rt_perf_xrun` | logs redactados, rendimiento medido contra baseline, sin claims de baja latencia sin medición |
| CI | `ci_exact_sha` | el SHA sujeto del run debe coincidir exactamente con el candidato autorizado |
| Hardware | `pcm_direct`, `pcm_managed`, `native_dsd`, `dop`, `dsd_pcm` | una evidencia independiente por familia y por frontera realmente observada |

La familia `dop` requiere prueba situada al menos en `DAC_RECEIVER` para marcar `PASS` del gate físico: una portadora PCM o una selección DoP no certifican la interpretación en el DAC. Igual exigencia para `native_dsd`. Un dispositivo sin capacidad se marca `CAPABILITY_UNSUPPORTED` y bloquea GO; no se maquilla como PASS. Si las pruebas no existen, `NOT_RUN`. Si una suite falla, `FAIL`. Nunca convertir `SKIP` en `PASS`.

### 2. Secuencia Fish segura — instalación futura controlada en OpenCode

Las órdenes siguientes son instrucciones para **el futuro operador de OpenCode en un checkout local explícitamente autorizado**; no se ejecutaron durante el trabajo en Drive. Ejecutar solo después de revisar AGENTS.md, Biblia R11-F11 y norma DAC V3.5. No se deben copiar ni superponer A26/A39/A41/A42/A43 como parches adicionales.

```fish
# Tras descargar EL ÚNICO parche A44 desde Google Drive:
set -gx PRIMARY_PHASE AP2-F11
set -l A44_PATCH /ruta/descargas/MICHI_SIGNAL_TRUTH_A44_CUMULATIVE.patch
set -l A44_SHA 'PEGAR_SHA256_PUBLICADO_EN_ADENDA_A44'
set -l BASE_HEAD d32228fbcc49c4f107e4295b1a70e31fde4d9b07

# Validación PREVIA sin cambios a GitHub, ni commits/staging:
test (git rev-parse HEAD) = $BASE_HEAD; or exit 2
test (count (git status --porcelain)) -eq 0; or exit 2
test (string length -- $A44_SHA) -eq 64; or exit 2
sha256sum $A44_PATCH
python scripts/phase2_context.py --phase AP2-F11 --receipt-json; or exit 2
python scripts/verify_audio_phase2_repository_alignment.py --phase AP2-F11; or exit 2
python scripts/verify_dac_repository_alignment.py; or exit 2
git apply --check $A44_PATCH; or exit 2

# El parche se aplica SOLO con autorización para modificar el checkout local.
# No implica autorización para alterar la Biblia, hacer commit ni publicar nada.
# Después de aplicar el único parche:
# git apply $A44_PATCH
# python scripts/migrate_michi_truth_names_a41.py --repo . --mode plan --output /tmp/michi_a44_rename_plan.json

# STOP NORMATIVO. Revisar los siete movimientos y la regla histórica de R11.
# Solo un operador con autorización normativa explícita activa el siguiente comando:
# python scripts/migrate_michi_truth_names_a41.py --repo . --mode apply --permit-governance-rename --allow-existing-changes --output /tmp/michi_a44_rename_apply.json

# Después de esa migración autorizada, sin cambiar HEAD ni llamar GitHub:
# python scripts/verify_michi_truth_product_integration.py --repo . --patch $A44_PATCH --patch-sha256 $A44_SHA --verify-migrated --receipt /tmp/michi_a44_integracion.json
# python scripts/migrate_michi_truth_names_a41.py --repo . --mode verify --output /tmp/michi_a44_rename_verify.json
```

**Nota:** el `--verify-migrated` exige un checkout completo con base HEAD exacta. Reconstruye en un clon **local** el candidato (sin acceso a GitHub) y compara las rutas y archivos con el checkout autorizado. Un resultado estático válido no aprueba el audio ni la interfaz gráfica.

### 3. Generar y evaluar los recibos A44

```fish
# Hacerlo después de aplicar A44, porque el script está incluido en el parche.
# El output se escribe en /tmp; nunca sobre archivos del proyecto.
python scripts/verify_michi_truth_a44_handoff.py init \
  --repo . --patch $A44_PATCH --patch-sha256 $A44_SHA \
  --output /tmp/michi_a44_receipts.json

# A continuación un operador ejecuta realmente cada gate y conserva sus logs,
# capturas y recibos en un directorio aislado. Actualiza únicamente las filas
# probadas del JSON, adjuntando nombre relativo, SHA-256, run_id, exit_code y boundary.
# python scripts/verify_michi_truth_a44_handoff.py evaluate \
#   --repo . --patch $A44_PATCH --patch-sha256 $A44_SHA \
#   --receipt /tmp/michi_a44_receipts.json \
#   --evidence-root /tmp/michi_a44_evidence \
#   --output /tmp/michi_a44_verdict.json
```

**Recepción:** el evaluador devuelve `NO_GO` ante gate ausente, omitido, inválido o con prueba insuficiente. Si todos los archivos declarados coinciden con sus hashes, devuelve `HUMAN_CANONICAL_REVIEW_REQUIRED`: ni siquiera 18/18 declaraciones permite cerrar F11 automáticamente. Solo el propietario normativo puede ratificar la evidencia real y decidir la fase. Nunca se debe incluir una ruta de música personal, serial USB, token, secreto de Michi Link, datos de cuenta o PCM crudo en recibos exportables.

### 4. Escenarios adversariales mínimos

- **Temporalidad:** A→B→A con plan reutilizado; source B pending frente a A active; EOS, STOP, cancel y callback tardío; desuscripción tras cierre QML.
- **DSP:** `requested` ≠ `effective`, bypass después de readback, host reiniciado con pipeline reciclado, PEQ/FIR sin readback y orden de filtros no observado.
- **Managed y DSD→PCM:** recepción de sesión `RUNNING` + F03 vigente + F05 readback + prueba owner; `MOTOR_EFFECTIVE` nunca se transforma en evidencia de DAC por sí solo.
- **Native DSD:** lectura de formato nativo sin inventar un `PcmTuple`; evidencia física o `UNOBSERVED`.
- **DoP:** diferenciar fuente DSD, carrier PCM y decodificación DAC. Carrier observable sin prueba de receptor = sin certificación física.
- **Direct y Shared:** tuple ALSA exacta cuando existe; ruta compartida no se convierte en Direct por fallback; no declarar `bit-perfect` o `MATCHED_COMPLETE` sin método M11.5.
- **UI/UX:** 900×600, 1024, 1100×700, 1920×1080, DPR 1/1.25/1.5/2; alto contraste, reduced motion, teclado, foco devuelto y compatibilidad Qt; único popup y renderer.
- **Rendimiento:** p50/p95/p99 de notificación y apertura, RSS, XRUN, bloqueos, callback RT y cero pérdida silenciosa de transiciones; comparar contra baseline de la misma máquina.
- **Rollback:** guardar aparte cualquier modificación local preexistente; no recomendar `git reset --hard`, `git clean -fd`, `git push` ni PR; reconstruir en copia temporal y validar exactitud antes de tocar los archivos del usuario.

### 5. Qué queda fuera de la afirmación de "100 % en Drive"

El 100 % de D01–D20 representa **entregables candidatos completos para OpenCode**, no aplicación efectiva de código en el repositorio, no pruebas en el DAC y no cierre regulatorio de F11. Mientras cualquiera de los gates anteriores siga `NOT_RUN`, el estado productivo sigue `ACTIVE / NO-GO`.
