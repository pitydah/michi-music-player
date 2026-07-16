#!/usr/bin/env python3
"""
Accessibility granular fixer for QML files under ui_qml/pages/ and ui_qml/components/.

Scans each .qml file and ensures every interactive control has complete accessibility.
Only ADD properties -- never remove or modify existing ones.
"""

import os
import re
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEARCH_DIRS = [
    os.path.join(PROJECT_ROOT, "ui_qml", "pages"),
    os.path.join(PROJECT_ROOT, "ui_qml", "components"),
]

# Track what we add
stats = {
    "files_modified": set(),
    "accessible_role": 0,
    "accessible_name": 0,
    "active_focus_on_tab": 0,
    "accessible_checked": 0,
    "keys_handlers": 0,
    "accessible_on_press": 0,
    "close_policy": 0,
    "close_on_escape": 0,
}


def has_property(lines, prop_name, start, end):
    """Check if a property exists in the given line range (same block)."""
    for i in range(start, min(end, len(lines))):
        stripped = lines[i].strip()
        # Match property at any indentation level
        if stripped.startswith(prop_name) or stripped.startswith("Accessible." + prop_name):
            return True
        # Stop if we hit another top-level property or closing brace
        if stripped and not stripped.startswith(" ") and not stripped.startswith("\t") and not stripped.startswith("property"):
            if stripped.startswith("}") or stripped.startswith("import") or stripped.startswith("/"):
                continue
            if i > start and not stripped.startswith("Accessible."):
                pass  # might still be in same block
    return False


def has_accessible_role(lines, start, end):
    for i in range(start, min(end, len(lines))):
        s = lines[i].strip()
        if s.startswith("Accessible.role:"):
            return True
    return False


def has_accessible_name(lines, start, end):
    for i in range(start, min(end, len(lines))):
        s = lines[i].strip()
        if s.startswith("Accessible.name:"):
            return True
    return False


def has_accessible_checked(lines, start, end):
    for i in range(start, min(end, len(lines))):
        s = lines[i].strip()
        if s.startswith("Accessible.checked:"):
            return True
    return False


def has_active_focus_on_tab(lines, start, end):
    for i in range(start, min(end, len(lines))):
        s = lines[i].strip()
        if s.startswith("activeFocusOnTab:"):
            return True
    return False


def has_keys_handler(lines, start, end, keyname):
    for i in range(start, min(end, len(lines))):
        s = lines[i].strip()
        if s.startswith("Keys.on" + keyname + ":"):
            return True
    return False


def has_close_policy(lines, start, end):
    for i in range(start, min(end, len(lines))):
        s = lines[i].strip()
        if s.startswith("closePolicy:"):
            return True
    return False


def find_block_end(lines, start):
    """Find the end of a QML component block starting at `start`."""
    depth = 0
    i = start
    opened = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Count { and }
        for ch in line:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            return i + 1
        if not opened and i > start:
            # no braces found in this line, try next
            pass
        i += 1
    return len(lines)


def find_component_blocks(content):
    """Find all component declarations and their line ranges."""
    blocks = []
    lines = content.split("\n")
    # Match component openings like: Button {   or   QQC2.Button {   or   Item {   or   Rectangle {
    component_pattern = re.compile(
        r"^(\s*)((QQC2\.|[A-Z]\w*\.)?(\w+))\s*\{$"
    )
    for i, line in enumerate(lines):
        m = component_pattern.match(line)
        if m:
            typename = m.group(4)
            block_start = i
            block_end = find_block_end(lines, block_start)
            blocks.append((typename, block_start, block_end, m.group(1), m.group(2)))
    return blocks, lines


def ensure_property(lines, insert_line, indent, prop_line, check_fn, start, end):
    """Add a property line if check_fn returns False."""
    if not check_fn(lines, start, end):
        stats[prop_line.split(":")[0].replace("Accessible.", "").replace("activeFocus", "active_focus").replace("close", "close")] = \
            stats.get(prop_line.split(":")[0].replace("Accessible.", "").replace("activeFocus", "active_focus").replace("close", "close"), 0) + 1
        lines.insert(insert_line, indent + "    " + prop_line + "\n")
        return True
    return False


def process_file(filepath):
    relpath = os.path.relpath(filepath, PROJECT_ROOT)
    with open(filepath, "r") as f:
        content = f.read()
    original = content
    blocks, lines = find_component_blocks(content)

    # Track lines we've already modified to avoid conflicts
    modified_lines = set()
    insertions = []  # (insert_at_line, line_content) - to be applied in reverse order

    for typename, block_start, block_end, indent, full_decl in blocks:
        # Determine role mappings
        role_map = {
            "Button": "Accessible.Button",
            "MichiButton": "Accessible.Button",
            "MichiIconButton": "Accessible.Button",
            "Slider": "Accessible.Slider",
            "MichiSlider": "Accessible.Slider",
            "TextField": "Accessible.EditableText",
            "TextArea": "Accessible.EditableText",
            "MichiTextField": "Accessible.EditableText",
            "MichiSearchField": "Accessible.EditableText",
            "SearchField": "Accessible.EditableText",
            "ComboBox": "Accessible.ComboBox",
            "MichiComboBox": "Accessible.ComboBox",
            "CheckBox": "Accessible.CheckBox",
            "CheckDelegate": "Accessible.CheckBox",
            "MichiCheckBox": "Accessible.CheckBox",
            "Switch": "Accessible.CheckBox",
            "MichiSwitch": "Accessible.CheckBox",
            "RadioButton": "Accessible.RadioButton",
            "MichiRadioButton": "Accessible.RadioButton",
            "Dialog": "Accessible.Dialog",
            "MichiDialog": "Accessible.Dialog",
            "Popup": "Accessible.Dialog",
            "ListView": "Accessible.List",
            "GridView": "Accessible.List",
            "TableView": "Accessible.Table",
            "TabBar": "Accessible.PageTabList",
            "MichiTabBar": "Accessible.PageTabList",
            "TabButton": "Accessible.PageTab",
            "Menu": "Accessible.PopupMenu",
            "MichiMenu": "Accessible.PopupMenu",
            "MenuItem": "Accessible.MenuItem",
            "MichiMenuItem": "Accessible.MenuItem",
            "ProgressBar": "Accessible.ProgressBar",
            "MichiProgressBar": "Accessible.ProgressBar",
            "MichiDoubleSpinBox": "Accessible.Pane",
            "TextInput": "Accessible.EditableText",
            "SpinBox": "Accessible.EditableText",
        }

        expected_role = role_map.get(typename)

        # Skip non-interactive types
        misc_skip = {"Text", "Image", "Rectangle", "Row", "Column", "RowLayout", "ColumnLayout",
                     "Item", "FocusScope", "Repeater", "Timer", "BusyIndicator",
                     "ToolTip", "Behavior", "NumberAnimation", "ColorAnimation",
                     "SequentialAnimation", "PropertyAnimation", "HoverHandler",
                     "StatusBadge", "StatusIndicator", "MichiBadge", "GlassMaterial",
                     "InputMaterial", "GlassCard", "GlassPanel", "HeroPanel",
                     "MichiCard", "MichiPanel", "MichiSection", "MichiTooltip",
                     "NotificationItem", "NotificationToast", "NotificationBanner",
                     "NotificationCenter", "NotificationProgressItem",
                     "NotificationAnnouncement", "ErrorAnnouncement",
                     "PlaybackStateAnnouncement",
                     "LoadingState", "EmptyState", "ErrorState", "UnavailableState",
                     "MichiLoadingState", "MichiEmptyState", "MichiErrorState",
                     "MichiUnavailableState", "MichiSkeleton", "MichiDeferredPhysicalState",
                     "ProgressState",
                     "PageStateManager", "LibraryPageStateGuard",
                     "MichiResponsive", "MichiVisualState", "MichiReducedMotion",
                     "MichiFocusRing", "InlineError", "InlineValidation",
                     "PageStateManager", "LibraryPageStateGuard",
                     "MichiResponsiveGrid", "MichiSplitView", "MichiPage",
                     "MichiToolbar", "MichiMetadataLine", "MichiStatCard",
                     "MichiTrackRow", "MichiListRow", "MichiArtistTile",
                     "MichiAlbumTile", "MichiListRow", "MichiPageHeader",
                     "MonoToggle", "ReducedMotionToggle",
                     "IconSlot", "SectionHeader",
                     "ServiceHealthBadge", "TrackQualityBadge",
                     "MichiLayoutRow", "MichiLayoutColumn",
                     "ResponsivePageLayout", "ResponsiveToolbar",
                     "PlaybackActionHandler", "JobStatusBanner", "JobProgressCard",
                     "KeyboardShortcutHint", "LyricsSearchDialog",
                     "SongContextMenu", "SortMenu", "SelectionActionBar",
                     "LibrarySelectionBar", "LibraryFilterBar", "LibraryNavigationBar",
                     "LibraryStatusHeader", "LibraryTrackHeader",
                     "LibrarySortMenu", "LibraryColumnSelector", "LibraryContextMenu",
                     "LibraryTrackContextMenu", "LibraryEmptyState", "LibraryErrorState",
                     "LibrarySearchField", "LibraryViewSelector", "LibraryPage",
                     "AlbumGrid", "AlbumGridView", "AlbumListView",
                     "ArtistList", "ArtistListView", "FolderBrowser", "FolderContentView",
                     "FolderTreeView", "FolderContextMenu", "FolderBreadcrumb",
                     "SongTable", "SongRow", "LibraryTrackRow", "LibraryTrackTable",
                     "AlbumCard", "ArtistCard", "SourceCard", "TrackStatusIndicators",
                     "SourceExclusionEditor", "SourceScanProgress",
                     "GenreDetailPage", "ComposerDetailPage",
                     "PlaylistCard", "PlaylistTrackList",
                     "QueueItem", "QueueListView", "QueueHistorySection",
                     "QueueHeader", "QueueEmptyState", "QueueActions",
                     "NowPlayingControls", "NowPlayingQueuePreview",
                     "NowPlayingQueuePanel", "NowPlayingVolume", "NowPlayingSeekBar",
                     "NowPlayingInfo", "NowPlayingCover", "NowPlayingBar",
                     "NowPlayingMetadata", "NowPlayingOutputSelector",
                     "NowPlayingProgress", "NowPlayingTechnicalInfo",
                     "NowPlayingHeader", "NowPlayingArtwork", "NowPlayingLyricsPane",
                     "ExpandedNowPlayingPanel", "SyncedLyricsView",
                     "MixRuleEditor", "MixGenerationProgress", "MixFeedbackControls",
                     "MixExplanationPanel", "MixExplanationDrawer",
                     "MetadataFieldRow", "MetadataFieldGrid",
                     "MetadataPreview", "MetadataDiffView", "MetadataConflictView",
                     "MetadataWriteProgress", "MetadataArtworkPreview",
                     "MetadataArtworkEditor", "MetadataSingleEditor",
                     "MetadataBatchEditor",
                     "OutputProfileCard", "OutputCapabilityView",
                     "OutputTestResult", "OutputProfileDetail",
                     "RadioStationDetail", "RadioSearchView",
                     "RadioImportExportPanel", "RadioImportDialog",
                     "RadioEditorDialog", "RadioEditDialog",
                     "SearchResultSection", "SearchResultRow", "SearchResultItem",
                     "SearchResultGroup", "SearchResultDelegate",
                     "SearchSuggestions", "SearchRecentQueries",
                     "SearchFiltersDrawer", "GlobalSearchOverlay",
                     "HomeHero", "LibraryStatusCard", "ContinueCard",
                     "EcosystemCard", "AssistantCard",
                     "ConfiguredServerCard", "ConnectionCard", "DiscoveredServerCard",
                     "ExternalServerCard", "ConnectionErrorPanel",
                     "ConnectionCapabilities", "NetworkDiscoveryPanel",
                     "ManualConnectionDialog", "PairingDialog",
                     "HomeAudioAccess", "MicroServerHero", "ServerDiscoveryView",
                     "DeviceCard", "DeviceCompatibilityView",
                     "DeviceStoragePanel", "DeviceStorageView",
                     "DeviceSyncHistory", "DeviceSyncProfileEditor",
                     "DeviceTransferJob", "DeviceTransferPanel", "DeviceTransferQueue",
                     "SyncStatusPanel", "DevicePairingDialog",
                     "HistoryFilterBar", "HistoryTable", "HistoryTimeline",
                     "HistoryStats", "HistoryExportDialog", "HistoryRetentionDialog",
                     "DSPModuleCard", "DSPConflictWarning",
                     "EqualizerBandControl", "EqualizerGraph", "EqualizerPresetBrowser",
                     "AudioInputSelection", "AudioSelectionSummary",
                     "AudioTechnicalReport", "AudioWaveformSummary",
                     "AudioComparisonPage", "ComparisonPanel",
                     "AudioJobDetail", "AudioLabResultsPage",
                     "DoctorRepairProgress", "DoctorIssueList", "DoctorIssueDetail",
                     "DoctorDryRunPage",
                     "LibraryDoctorReport", "LibraryDoctorProgress",
                     "LibraryDoctorOverview", "LibraryDoctorIssueList",
                     "LibraryDoctorIssueDetail", "LibraryDoctorFixPreview",
                     "LibraryDoctorScanPage", "DoctorReportPage",
                     "DiscLabPage",
                     "BaseDialog", "ConfirmDialog", "DestructiveDialog", "InputDialog",
                     "ToastHost", "InspectorPanel",
                     "FilterChip", "SidebarItem",
                     }

        if typename in misc_skip:
            continue

        if typename in {"MouseArea", "DropArea"}:
            continue

        # If no role mapping, skip
        if expected_role is None:
            continue

        # --- 1. Accessible.role ---
        if expected_role.startswith("Accessible."):
            if not has_accessible_role(lines, block_start, block_end):
                role_val = expected_role.split(".")[1]
                insert_at = block_start + 1
                # Find a good insertion point: after opening brace, before child components
                lines.insert(insert_at, indent + "    Accessible.role: Accessible." + role_val + "\n")
                block_end += 1
                stats["accessible_role"] = stats.get("accessible_role", 0) + 1
                stats["files_modified"].add(filepath)

        # --- 2. Accessible.name ---
        if typename in {"MichiButton", "MichiIconButton", "MichiSlider", "MichiTextField",
                         "MichiSearchField", "MichiCheckBox", "MichiSwitch",
                         "MichiRadioButton", "MichiComboBox", "MichiDialog",
                         "MichiTabBar", "MichiMenuItem",
                         "MichiProgressBar", "MichiDoubleSpinBox",
                         "SearchField", "MonoToggle", "ReducedMotionToggle",
                         "SidebarItem", "FilterChip", "PageHeader",
                         "DiscoveryResultCard", "HeaderBar",
                         "SettingRow", "SettingsRow",
                         # also some page-level items
                         }:
            # These already have accessibleName property
            pass
        else:
            if not has_accessible_name(lines, block_start, block_end):
                is_text_field = typename in {"TextField", "TextArea", "TextInput"}
                name_val = '"' + typename + '"' if not is_text_field else '"Campo de texto"'
                if is_text_field:
                    name_val = '"Campo de texto"'
                insert_at = block_start + 1
                while insert_at < block_end - 1:
                    s = lines[insert_at].strip()
                    if s.startswith("Accessible.role:"):
                        insert_at += 1
                        break
                    if s.startswith("id:") or s.startswith("objectName:") or s.startswith("property") or s.startswith("signal"):
                        insert_at += 1
                    else:
                        break
                lines.insert(insert_at, indent + "    Accessible.name: " + name_val + "\n")
                block_end += 1
                stats["accessible_name"] = stats.get("accessible_name", 0) + 1
                stats["files_modified"].add(filepath)

        # --- 3. activeFocusOnTab: true ---
        if typename not in {"SidebarItem", "FilterChip", "MonoToggle", "ReducedMotionToggle",
                             "PageHeader", "DiscoveryResultCard",
                             "MichiTabBar", "MichiMenuItem",
                             }:
            if not has_active_focus_on_tab(lines, block_start, block_end):
                if typename not in {"Text", "Image", "Rectangle", "Row", "Column",
                                     "RowLayout", "ColumnLayout", "Item", "FocusScope",
                                     "Repeater", "Behavior", "NumberAnimation",
                                     "ColorAnimation", "SequentialAnimation", "PropertyAnimation",
                                     "HoverHandler", "ToolTip", "BusyIndicator", "Timer",
                                     "GlassMaterial", "InputMaterial"}:
                    insert_at = block_start + 1
                    while insert_at < block_end - 1:
                        s = lines[insert_at].strip()
                        if s.startswith("Accessible.") or s.startswith("id:") or s.startswith("objectName:") or s.startswith("property"):
                            insert_at += 1
                        else:
                            break
                    if not lines[insert_at].strip().startswith("activeFocusOnTab:"):
                        lines.insert(insert_at, indent + "    activeFocusOnTab: true\n")
                        block_end += 1
                        stats["active_focus_on_tab"] = stats.get("active_focus_on_tab", 0) + 1
                        stats["files_modified"].add(filepath)

        # --- 4. Accessible.checked for CheckBox/Switch/RadioButton ---
        if typename in {"MichiCheckBox", "MichiSwitch", "MichiRadioButton",
                         "CheckBox", "Switch", "RadioButton", "CheckDelegate"}:
            if not has_accessible_checked(lines, block_start, block_end):
                insert_at = block_start + 1
                while insert_at < block_end - 1:
                    s = lines[insert_at].strip()
                    if s.startswith("Accessible."):
                        insert_at += 1
                    else:
                        break
                lines.insert(insert_at, indent + "    Accessible.checked: root.checked\n")
                block_end += 1
                stats["accessible_checked"] = stats.get("accessible_checked", 0) + 1
                stats["files_modified"].add(filepath)

        # --- 5. Keys handlers for MouseArea items ---
        # Check if this component has a MouseArea but no Keys handlers
        has_ma = False
        has_return_key = False
        has_space_key = False
        has_on_press = False
        for j in range(block_start, block_end):
            s = lines[j].strip()
            if s.startswith("MouseArea"):
                has_ma = True
            if s.startswith("Keys.onReturnPressed"):
                has_return_key = True
            if s.startswith("Keys.onSpacePressed"):
                has_space_key = True
            if "Accessible.onPressAction" in s:
                has_on_press = True

        # For components with MouseArea but no keyboard handling, add Keys + Accessible.onPressAction
        if has_ma and not has_return_key and not has_space_key and not has_on_press:
            if typename not in {"MichiSlider", "MichiCheckBox", "MichiSwitch",
                                 "MichiRadioButton", "MichiComboBox", "MichiTabBar",
                                 "MichiButton", "MichiIconButton", "MichiDialog",
                                 "MichiMenuItem", "MichiMenu"}:
                # Add Keys.onReturnPressed and Keys.onSpacePressed before closing brace
                if not has_return_key and not has_space_key:
                    # Find the closing brace
                    close_brace_line = block_end - 1
                    while close_brace_line > block_start and lines[close_brace_line].strip() != "}":
                        close_brace_line -= 1
                    if close_brace_line > block_start:
                        # Check if the handler would be redundant
                        # Only add if the component has a signal that suggests interactivity
                        has_clicked = False
                        has_toggled = False
                        for j in range(block_start, block_end):
                            s = lines[j].strip()
                            if "signal clicked" in s or "signal toggled" in s:
                                has_clicked = True
                                break
                        if has_clicked:
                            lines.insert(close_brace_line, indent + "    Keys.onSpacePressed: function(event) {\n")
                            lines.insert(close_brace_line + 1, indent + "        root.clicked()\n")
                            lines.insert(close_brace_line + 2, indent + "        event.accepted = true\n")
                            lines.insert(close_brace_line + 3, indent + "    }\n")
                            lines.insert(close_brace_line + 4, indent + "\n")
                            lines.insert(close_brace_line + 5, indent + "    Keys.onReturnPressed: function(event) {\n")
                            lines.insert(close_brace_line + 6, indent + "        root.clicked()\n")
                            lines.insert(close_brace_line + 7, indent + "        event.accepted = true\n")
                            lines.insert(close_brace_line + 8, indent + "    }\n")
                            block_end += 9
                            stats["keys_handlers"] = stats.get("keys_handlers", 0) + 1
                            stats["files_modified"].add(filepath)

        # --- 6. Accessible.onPressAction for interactive items ---
        if has_ma and not has_on_press and not has_return_key:
            if typename in {"FilterChip", "SidebarItem", "DiscoveryResultCard"}:
                # Add onPressAction alongside role
                for j in range(block_start, block_end):
                    s = lines[j].strip()
                    if s.startswith("Accessible.role:"):
                        # Insert after this line
                        lines.insert(j + 1, indent + "    Accessible.onPressAction: root.clicked\n")
                        block_end += 1
                        stats["accessible_on_press"] = stats.get("accessible_on_press", 0) + 1
                        stats["files_modified"].add(filepath)
                        break

        # --- 7. closePolicy: Popup.CloseOnEscape for Dialogs ---
        if typename in {"MichiDialog", "Dialog", "Popup"}:
            if not has_close_policy(lines, block_start, block_end):
                insert_at = block_start + 1
                while insert_at < block_end - 1:
                    s = lines[insert_at].strip()
                    if s.startswith("Accessible.") or s.startswith("id:") or s.startswith("objectName:") or s.startswith("property"):
                        insert_at += 1
                    else:
                        break
                lines.insert(insert_at, indent + "    closePolicy: Popup.CloseOnEscape\n")
                block_end += 1
                stats["close_on_escape"] = stats.get("close_on_escape", 0) + 1
                stats["files_modified"].add(filepath)

    # Apply all insertions in reverse order

    new_content = "\n".join(lines)
    if new_content != original:
        with open(filepath, "w") as f:
            f.write(new_content)


def main():
    qml_files = []
    for d in SEARCH_DIRS:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith(".qml"):
                    qml_files.append(os.path.join(root, f))

    print(f"Found {len(qml_files)} .qml files to scan")
    for fp in qml_files:
        process_file(fp)

    print(f"\n{'='*50}")
    print(f"Files modified: {len(stats['files_modified'])}")
    print(f"Accessible.role added: {stats.get('accessible_role', 0)}")
    print(f"Accessible.name added: {stats.get('accessible_name', 0)}")
    print(f"activeFocusOnTab added: {stats.get('active_focus_on_tab', 0)}")
    print(f"Accessible.checked added: {stats.get('accessible_checked', 0)}")
    print(f"Keys handlers added: {stats.get('keys_handlers', 0)}")
    print(f"Accessible.onPressAction added: {stats.get('accessible_on_press', 0)}")
    print(f"closePolicy added: {stats.get('close_on_escape', 0)}")


if __name__ == "__main__":
    main()
