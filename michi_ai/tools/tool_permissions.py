"""ToolPermission levels for Michi AI tools."""

from __future__ import annotations


class ToolPermission:
    READ_ONLY = "read_only"
    SAFE_ACTION = "safe_action"
    RESOURCE_INTENSIVE = "resource_intensive"
    WRITES_METADATA = "writes_metadata"
    FILE_OPERATION = "file_operation"
    NETWORK_OPERATION = "network_operation"
    CONFIG_CHANGE = "config_change"
    DESTRUCTIVE = "destructive"


REQUIRES_CONFIRMATION = {
    ToolPermission.RESOURCE_INTENSIVE,
    ToolPermission.WRITES_METADATA,
    ToolPermission.FILE_OPERATION,
    ToolPermission.NETWORK_OPERATION,
    ToolPermission.CONFIG_CHANGE,
    ToolPermission.DESTRUCTIVE,
}


def permission_requires_confirmation(permission: str) -> bool:
    return permission in REQUIRES_CONFIRMATION
