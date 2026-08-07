"""Fase Sync architecture gates — single authority for device sync.

The DeviceSyncService facade must NOT contain the parallel system:
no threading, no ``self._jobs`` registry, no ``hash(path)`` serials, no
direct subprocess (ProcessController only), no internal trust store, and
no brand-name protocol detection. The durable device_sync handler is
registered in composition with owner-scoped jobs.

All source scans strip docstrings and comments: documentation may
reference the removed patterns without implying they exist in code.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FACADE = PROJECT_ROOT / "core" / "device_sync_service.py"
MODELS = PROJECT_ROOT / "core" / "device_sync" / "models.py"
IDENTITY = PROJECT_ROOT / "core" / "device_sync" / "identity.py"
DISCOVERY = PROJECT_ROOT / "core" / "device_sync" / "discovery.py"
TRANSFER = PROJECT_ROOT / "core" / "device_sync" / "transfer.py"
RESOLVER = PROJECT_ROOT / "core" / "device_sync" / "profile_resolver.py"
COMPOSITION_JOBS = PROJECT_ROOT / "core" / "composition" / "jobs.py"
PORTS = PROJECT_ROOT / "core" / "jobs" / "ports.py"

_DOCSTRING_RE = re.compile(r'"""[\s\S]*?"""', re.MULTILINE)


def _code(path: Path) -> str:
    """Source without docstrings or comment lines (documentation may
    reference removed patterns; the gates apply to executable code)."""
    text = _DOCSTRING_RE.sub("", path.read_text(encoding="utf-8"))
    lines = [ln for ln in text.splitlines()
             if not ln.lstrip().startswith("#")]
    return "\n".join(lines)


class TestFacadeSingleAuthority:
    def test_no_threading_import(self):
        assert "import threading" not in _code(FACADE)
        assert "from threading" not in _code(FACADE)

    def test_no_parallel_jobs_registry(self):
        assert "self._jobs" not in _code(FACADE)

    def test_no_job_counter(self):
        assert "_job_counter" not in _code(FACADE)

    def test_no_internal_trust_store(self):
        text = _code(FACADE)
        assert not re.search(r"self\._paired(?![A-Za-z_])", text)
        assert "_callbacks" not in text

    def test_no_in_memory_history_list(self):
        text = _code(FACADE)
        assert "self._history_repository" in text  # injected repository
        assert "_max_history" not in text
        assert "self._history: list" not in text

    def test_no_hash_mount_path_serial(self):
        text = _code(FACADE)
        assert "hash(mount" not in text
        assert "str(hash(" not in text

    def test_no_direct_subprocess(self):
        assert "import subprocess" not in _code(FACADE)
        assert "subprocess.run" not in _code(FACADE)
        assert "subprocess.Popen" not in _code(FACADE)

    def test_subprocess_only_in_controlled_port(self):
        # The only subprocess plumbing in the pipeline package is the MTP
        # probe (ProcessController); transfer never runs tools directly.
        discovery = _code(DISCOVERY)
        transfer = _code(TRANSFER)
        assert "process_controller" in discovery
        assert "subprocess.PIPE" in discovery  # MTP probe plumbing only
        assert "subprocess.run" not in discovery
        assert "subprocess.run" not in transfer
        assert "subprocess.Popen" not in transfer

    def test_facade_never_constructs_pipeline_services(self):
        text = _code(FACADE)
        for name in (
            "DeviceRegistry(",
            "SyncPlanner(",
            "TranscodePlanner(",
            "TransferAdapter(",
            "VerificationService(",
            "SyncHistoryRepository(",
            "MscDiscoveryAdapter(",
            "MtpDiscoveryAdapter(",
        ):
            assert name not in text, f"facade constructs {name}"

    def test_no_brand_detection_for_protocol(self):
        # Brands are only capability-profile hints in the resolver; the
        # discovery adapters never classify protocol by brand name.
        discovery = _code(DISCOVERY)
        assert "hiby" not in discovery.lower()
        assert "fiio" not in discovery.lower()
        resolver = _code(RESOLVER)
        assert "BRAND" in resolver  # brand hints exist as profiles only


class TestIdentityChain:
    def test_priority_chain_implemented(self):
        text = _code(IDENTITY)
        for step in (
            "USB_SERIAL",
            "MTP_ID",
            "FILESYSTEM_UUID",
            "VENDOR_PRODUCT_VOLUME_UUID",
            "PERSISTED_FINGERPRINT",
            "UNSTABLE_FALLBACK",
        ):
            assert step in text, f"identity chain missing {step}"

    def test_models_never_use_hash_for_serial(self):
        assert "hash(" not in _code(MODELS)

    def test_no_builtin_hash_in_identity_module(self):
        # sha256 fingerprints are fine; builtin hash() is not.
        assert "hash(" not in _code(IDENTITY)

    def test_unstable_fallback_explicitly_flagged(self):
        text = _code(IDENTITY)
        assert "identity_unstable" in text
        assert "UNSTABLE_FALLBACK" in text


class TestJobWiring:
    def test_device_sync_handler_registered_in_composition(self):
        text = _code(COMPOSITION_JOBS)
        assert '"device_sync"' in text
        assert "make_device_sync_handler" in text
        assert "make_device_transfer_handler" in text

    def test_port_registered_without_service_construction(self):
        text = _code(COMPOSITION_JOBS)
        assert "_DeviceSyncPort" in text
        assert "DeviceSyncService(" not in text

    def test_owner_scoped_jobs(self):
        facade = _code(FACADE)
        assert 'owner=f"device:{device_id}"' in facade
        assert 'owner="device:transfer"' in facade
        assert "cancel_all" not in facade

    def test_ports_declare_sync_surface(self):
        text = _code(PORTS)
        assert "sync_device" in text
        assert "transfer_file" in text
