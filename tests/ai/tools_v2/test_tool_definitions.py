from __future__ import annotations

from michi_ai.v2.core.models import PermissionLevel
from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS

_DESTRUCTIVE_REQUIRE_CONFIRMATION = {
    "delete_playlist", "apply_library_repair", "rollback_library_repair",
}
_CONFIRMATION_EXEMPT_READONLY = {
    "replace_queue", "clear_queue", "start_device_sync",
    "apply_setting_change", "restore_setting", "start_conversion",
}


class TestToolDefinitionsCompleteness:
    def test_all_tools_have_names(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert defn.name, f"Tool missing name: {defn}"

    def test_all_tools_have_descriptions(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert defn.description, f"Tool '{defn.name}' missing description"

    def test_all_tools_have_permissions(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert defn.permission, f"Tool '{defn.name}' missing permission"

    def test_all_tools_have_capabilities(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert len(defn.capabilities) > 0, f"Tool '{defn.name}' missing capabilities"

    def test_all_tools_have_timeout(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert defn.timeout_seconds > 0, f"Tool '{defn.name}' missing timeout"

    def test_no_duplicate_names(self):
        names = [d.name for d in BUILTIN_TOOL_DEFINITIONS]
        assert len(names) == len(set(names)), f"Duplicate names: {[n for n in names if names.count(n) > 1]}"

    def test_destructive_tools_require_confirmation(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            if defn.destructive:
                assert defn.requires_confirmation, (
                    f"Tool '{defn.name}' is destructive but does not require confirmation"
                )

    def test_read_only_tools_dont_require_confirmation(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            if defn.permission == PermissionLevel.READ_ONLY:
                assert not defn.requires_confirmation, (
                    f"Tool '{defn.name}' is READ_ONLY but requires confirmation"
                )

    def test_expected_count(self):
        assert len(BUILTIN_TOOL_DEFINITIONS) >= 55, f"Expected >=55 tools, got {len(BUILTIN_TOOL_DEFINITIONS)}"

    def test_ids_have_no_spaces(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert " " not in defn.name, f"Tool '{defn.name}' has space"

    def test_all_handlers_are_placeholder(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert defn.handler is None, f"Tool '{defn.name}' has a handler in definitions (should be added at registration)"


class TestToolDefinitionsSchema:
    def test_required_args_have_properties(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            schema = defn.input_schema
            required = schema.get("required", [])
            props = schema.get("properties", {})
            for req in required:
                assert req in props, f"Tool '{defn.name}': required arg '{req}' missing from properties"

    def test_volume_range(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            if defn.name == "set_volume":
                vol = defn.input_schema["properties"]["volume"]
                assert vol.get("minimum") == 0
                assert vol.get("maximum") == 100

    def test_track_ids_max_items(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            props = defn.input_schema.get("properties", {})
            for name, prop in props.items():
                if ("track_ids" in name or name == "track_ids") and prop.get("type") == "array":
                    assert prop.get("maxItems", 0) > 0, (
                        f"Tool '{defn.name}' arg '{name}' array missing maxItems"
                    )

    def test_cancellable_tools_have_reasonably_high_timeout(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            if defn.cancellable:
                assert defn.timeout_seconds >= 5, (
                    f"Tool '{defn.name}' is cancellable but timeout is only {defn.timeout_seconds}s"
                )


class TestToolDefinitionsPermissions:
    def test_permission_levels_are_valid(self):
        valid = set(PermissionLevel)
        for defn in BUILTIN_TOOL_DEFINITIONS:
            assert defn.permission in valid, f"Tool '{defn.name}' has invalid permission: {defn.permission}"

    def test_no_empty_capabilities(self):
        for defn in BUILTIN_TOOL_DEFINITIONS:
            for cap in defn.capabilities:
                assert cap, f"Tool '{defn.name}' has empty capability"

    def test_rollback_tool_exists_when_declared(self):
        names = {d.name for d in BUILTIN_TOOL_DEFINITIONS}
        for defn in BUILTIN_TOOL_DEFINITIONS:
            if defn.rollback_tool:
                assert defn.rollback_tool in names, (
                    f"Tool '{defn.name}' declares rollback '{defn.rollback_tool}' but not in definitions"
                )
