# ADR-007: Pairing móvil seguro (challenge-response Ed25519)

## Status

Accepted (Fase 7 de P0 stabilization — commit `c171400f`)

## Context

El pairing móvil se autenticaba con un HMAC de un código de 6 dígitos
(`core/mobile_sync_service.py:314-326`, falso éxito #9 del baseline): el dispositivo
demostraba conocer el código, no la posesión de la clave privada. Un atacante que
observara o adivinara el código podía registrar su clave pública como confiable.
Además:

- El fingerprint del dispositivo se derivaba del lado del **cliente** (auto-afirmado):
  el servidor confiaba en un dato que el propio solicitante podía fabricar.
- El modo legacy (código sin firma) seguía activo de forma general, sin restricción de
  red ni caducidad, y sin registro de auditoría.
- La persistencia de la confianza no era transaccional: un fallo de escritura podía
  dejar el paring "aprobado" en memoria y no en disco, o viceversa.

Evidencia: `audit_capability_truthfulness.py` (F11) y
`test_mobile_pairing_no_unverified_fingerprint.py` (gate de arquitectura) detectaban el
fingerprint no verificado y el flujo de confianza sin prueba criptográfica.

## Decision

El pairing usa **challenge-response con Ed25519** (`cryptography`) y la confianza se
persiste de forma transaccional:

1. **Challenge-response Ed25519**: el servidor emite un challenge (nonce) **single-use**;
   el dispositivo firma el challenge con su clave privada; el servidor verifica con la
   clave pública registrada. Sin firma válida no hay confianza
   (`test_valid_signature_pairing`, `test_invalid_signature_rejected`).
2. **Fingerprint derivado server-side**: el fingerprint del dispositivo se calcula en el
   servidor a partir de la clave pública verificada — el cliente no puede auto-afirmar su
   identidad (`test_code_without_signature_fails`).
3. **Legacy code-only deshabilitado por defecto**: el flujo de solo-código queda
   restringido a loopback, con TTL de 300s y auditoría; si no está explícitamente
   habilitado en config segura, falla marcado (`test_legacy_mode_flagged`).
4. **`PERSISTENCE_FAILED`**: si la escritura de la confianza falla, el pairing se invalida
   en memoria y en disco — nunca queda a medio camino (`test_persistence_failure_invalidates`).
5. **`DeviceRegistry` inyectado**: el registry de dispositivos se recibe por inyección
   (autoridad única, ADR-002) — el servicio no construye su propio registro paralelo.
6. **Listener bound subclass sin estado de clase**: el listener de pairing hereda de un
   subclass sin atributos de clase compartidos (evita estado global accidental) y
   verifica mount/red antes de aceptar conexiones.
7. **Hardening de red**: `bind_host` / `allowed_networks` / `tls_mode` configuran la
   superficie de exposición del listener.

## Consequences

### Positive

- La confianza exige prueba de posesión de clave privada: un código observado ya no
  basta.
- El fingerprint es generado por el servidor: la identidad no es fabricable por el
  cliente.
- El modo legacy queda acotado (loopback + TTL + auditoría) y marcado; el camino
  firmado es el único de confianza plena.
- Tests de seguridad de caja negra: `test_mobile_pairing_signature.py` (5+),
  `test_mobile_pairing_persistence.py`, `test_mobile_trust_revocation.py`.

### Negative

- Complejidad criptográfica nueva: gestión de pares Ed25519 y nonces single-use en el
  cliente móvil y el servidor — requiere sincronización de versiones del app móvil.
- El loopback-only del legacy rompe el pairing por código en redes locales reales hasta
  que la app móvil soporte firma (migración en curso, no bloqueante del camino seguro).
- `allowed_networks` mal configurada puede aislar dispositivos legítimos; la
  configuración por defecto es conservadora.

### Migration

- El flujo HMAC de 6 dígitos quedó deshabilitado fuera de loopback con TTL y audit;
  no se eliminó la ruta (compatibilidad de lectura de pares legacy ya persistidos).
- Los pares existentes migran al fingerprint server-derived en el primer re-pairing
  (no se fuerza re-pairing en masa).
- `mobile_sync_service` delegó el registry en `DeviceRegistry` inyectado; los tests
  e2e de pairing se actualizaron al flujo firmado.

## Alternatives considered

- **HMAC con código + clave pública (status quo)**: rechazado — no prueba posesión de
  clave; el código viaja por la red.
- **TLS mutual (mTLS) con certificados**: rechazado — sobrecarga de PKI para el pairing
  de un jugador móvil doméstico; Ed25519 challenge-response cubre el mismo objetivo con
  un intercambio mínimo.
- **Pairing por presencia (QR local + PIN)**: descartado como flujo único — válido como
  UX futura, pero no sustituye la verificación criptográfica de identidad posterior.
- **Trust-on-first-use (TOFU)**: rechazado — el fingerprint auto-afirmado del cliente es
  precisamente el vector del falso éxito #9.
