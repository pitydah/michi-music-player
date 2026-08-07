"""Architecture tests — manifest↔composition contract and lifecycle invariants.

These tests enforce ADR-001 (declarative service manifest) and the runtime
service architecture audit (RUNTIME_SERVICE_AUDIT_CURRENT §4-5): every key
registered by the composition builders must have a manifest descriptor, all
MANAGED components must be started/shut down exactly once, and duplicate or
legacy components must never leak into productive composition.
"""
