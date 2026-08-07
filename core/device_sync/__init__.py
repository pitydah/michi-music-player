"""Device sync pipeline package (Fase Sync, P0 stabilization).

Canonical pipeline (all dependencies injected by composition):

    DeviceRegistry (canonical, injected)
    → DeviceDiscoveryAdapters (MSC / MTP / Michi Link)
    → DeviceProfileResolver
    → SyncPlanner → TranscodePlanner
    → DurableJobService (device_sync / device_transfer jobs)
    → TransferAdapter (ProcessController for external tools)
    → VerificationService
    → SyncHistoryRepository (app DB, migration 10)

The ``DeviceSyncService`` facade (``core.device_sync_service``) only
composes these; it owns no threads, no parallel job registry, no
in-memory history and no direct subprocess calls.
"""

from core.device_sync import (  # noqa: F401
    discovery,
    history,
    identity,
    models,
    planning,
    profile_resolver,
    transcode_planning,
    transfer,
    verification,
)
