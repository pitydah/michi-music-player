"""All stateful runtime components (Manager/Registry/Executor/Store) are manifested."""
from __future__ import annotations

from core.service_manifest import SERVICE_MANIFEST

# component name -> manifest key
RUNTIME_COMPONENTS: dict[str, str] = {
    "WorkerManager": "worker_manager",
    "QueryExecutor": "query_executor",
    "JobManager": "job_manager",
    "DurableJobService": "job_service",
    "JobBridge": "job_bridge",
    "AudioLabJobAdapter": "audio_lab_job_adapter",
    "ActionRegistry": "action_registry",
    "ActionRegistryBinder": "action_registry_binder",
    "SelectionContextBridge": "selection_context_bridge",
    "BridgeFactory": "bridge_factory",
    "DeviceRegistry": "device_registry",
    "ProviderManager": "provider_manager",
    "MpdServiceManager": "mpd_service_manager",
    "SnapserverManager": "snapserver_manager",
    "SnapcastControl": "snapcast_control",
    "SettingsRuntimeCoordinator": "settings_coordinator",
    "HybridAudioManager": "hybrid_audio_manager",
    "KnowledgeBroker": "knowledge_broker",
    "PageStateStore": "page_state_store",
}


def test_all_runtime_components_manifested() -> None:
    missing = [
        name for name, key in RUNTIME_COMPONENTS.items()
        if key not in SERVICE_MANIFEST
    ]
    assert missing == [], (
        f"Runtime components without manifest entries: {missing}"
    )


def test_legacy_job_components_marked_legacy() -> None:
    from core.service_manifest import ServiceClass

    assert SERVICE_MANIFEST["job_manager"].service_class == ServiceClass.LEGACY_COMPONENT
    assert (
        SERVICE_MANIFEST["audio_lab_job_adapter"].service_class
        == ServiceClass.LEGACY_COMPONENT
    )


def test_executors_and_process_managers_classified() -> None:
    from core.service_manifest import ServiceClass

    assert SERVICE_MANIFEST["worker_manager"].service_class == ServiceClass.EXECUTOR
    assert SERVICE_MANIFEST["query_executor"].service_class == ServiceClass.EXECUTOR
    assert (
        SERVICE_MANIFEST["snapserver_manager"].service_class
        == ServiceClass.PROCESS_MANAGER
    )
    assert (
        SERVICE_MANIFEST["mpd_service_manager"].service_class
        == ServiceClass.PROCESS_MANAGER
    )
    assert SERVICE_MANIFEST["device_registry"].service_class == ServiceClass.REGISTRY
    assert SERVICE_MANIFEST["action_registry"].service_class == ServiceClass.REGISTRY
    assert SERVICE_MANIFEST["provider_manager"].service_class == ServiceClass.REGISTRY
