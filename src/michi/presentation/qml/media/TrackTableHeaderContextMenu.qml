import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// Track table header context menu — R10 V2 (V4 §12).
//
// El menú emite INTENTS; LibraryTrackColumnState (vía el header) es el
// único que muta el estado — nunca doble aplicación.
MichiMenu {
    id: root

    property string targetColumn: ""
    property string targetLabel: ""
    property bool targetSortable: false
    property bool hasFallback: false
    property bool isSelected: false

    signal sortAscendingRequested(string column)
    signal sortDescendingRequested(string column)
    signal hideColumnRequested(string column)
    signal resetWidthRequested(string column)
    signal resetWidthsRequested()
    signal restoreDefaultsRequested()
    signal presetRequested(string name)
    signal toggleColumnRequested(string column)

    function applyPreset(name) {
        root.presetRequested(name)
    }

    // ── A) Contexto de CELL (compacto) ────────────────────────────────────
    MichiMenuHeader {
        text: qsTr("TRACK TABLE")
        visible: root.targetColumn !== ""
    }
    MichiMenuItem {
        text: qsTr("Sort Ascending")
        icon.name: "sort-ascending"
        visible: root.targetColumn !== "" && root.targetSortable
        onTriggered: root.sortAscendingRequested(root.targetColumn)
    }
    MichiMenuItem {
        text: qsTr("Sort Descending")
        icon.name: "sort-descending"
        visible: root.targetColumn !== "" && root.targetSortable
        onTriggered: root.sortDescendingRequested(root.targetColumn)
    }
    MichiMenuItem {
        text: qsTr("Hide %1").arg(root.targetLabel)
        icon.name: "eye-off"
        visible: root.targetColumn !== "" && root.targetColumn !== "title"
        onTriggered: root.hideColumnRequested(root.targetColumn)
    }
    MichiMenuItem {
        text: qsTr("Reset %1 Width").arg(root.targetLabel)
        icon.name: "reset"
        visible: root.targetColumn !== "" && root.targetColumn !== "actions"
        onTriggered: root.resetWidthRequested(root.targetColumn)
    }
    MichiSeparator { visible: root.targetColumn !== "" }

    // ── B) Preset (submenú nativo real) ───────────────────────────────────
    MichiMenu {
        title: qsTr("Preset")
        icon.name: "preset"

        function rebuild() {
            presetEssential.checked =
                LibraryTrackColumnState.currentPreset() === "essential"
            presetAudiophile.checked =
                LibraryTrackColumnState.currentPreset() === "audiophile"
            presetMetadata.checked =
                LibraryTrackColumnState.currentPreset() === "metadata"
            presetMinimal.checked =
                LibraryTrackColumnState.currentPreset() === "minimal"
        }
        onAboutToShow: rebuild()

        MichiMenuItem {
            id: presetEssential
            text: qsTr("Essential")
            checkable: true
            onTriggered: root.presetRequested("essential")
        }
        MichiMenuItem {
            id: presetAudiophile
            text: qsTr("Audiophile")
            checkable: true
            onTriggered: root.presetRequested("audiophile")
        }
        MichiMenuItem {
            id: presetMetadata
            text: qsTr("Metadata")
            checkable: true
            onTriggered: root.presetRequested("metadata")
        }
        MichiMenuItem {
            id: presetMinimal
            text: qsTr("Minimal")
            checkable: true
            onTriggered: root.presetRequested("minimal")
        }
    }

    // ── C) Columns (submenú nativo real con la jerarquía de secciones) ───
    MichiMenu {
        title: qsTr("Columns")
        icon.name: "sliders"

        MichiMenuHeader { text: qsTr("IDENTITY") }
        MichiMenuItem {
            text: qsTr("Artwork")
            checkable: true
            checked: LibraryTrackColumnState.artworkVisible
            onTriggered: root.toggleColumnRequested("artwork")
        }
        MichiMenuItem {
            text: qsTr("Title (required)")
            icon.name: "lock"
            enabled: false
        }

        MichiMenuHeader { text: qsTr("MUSICAL CONTEXT") }
        MichiMenuItem {
            text: qsTr("Artist")
            checkable: true
            checked: LibraryTrackColumnState.artistVisible
            onTriggered: root.toggleColumnRequested("artist")
        }
        MichiMenuItem {
            text: qsTr("Album")
            checkable: true
            checked: LibraryTrackColumnState.albumVisible
            onTriggered: root.toggleColumnRequested("album")
        }

        MichiMenuHeader { text: qsTr("AUDIO") }
        MichiMenuItem {
            text: qsTr("Format")
            checkable: true
            checked: LibraryTrackColumnState.formatVisible
            onTriggered: root.toggleColumnRequested("format")
        }
        MichiMenuItem {
            text: qsTr("Sample Rate")
            checkable: true
            checked: LibraryTrackColumnState.sampleRateVisible
            onTriggered: root.toggleColumnRequested("sampleRate")
        }
        MichiMenuItem {
            text: qsTr("Bit Depth")
            checkable: true
            checked: LibraryTrackColumnState.bitDepthVisible
            onTriggered: root.toggleColumnRequested("bitDepth")
        }
        MichiMenuItem {
            text: qsTr("DSD Rate")
            checkable: true
            checked: LibraryTrackColumnState.dsdRateVisible
            onTriggered: root.toggleColumnRequested("dsdRate")
        }
        MichiMenuItem {
            text: qsTr("Bitrate")
            checkable: true
            checked: LibraryTrackColumnState.bitrateVisible
            onTriggered: root.toggleColumnRequested("bitrate")
        }
        MichiMenuItem {
            text: qsTr("Channels")
            checkable: true
            checked: LibraryTrackColumnState.channelsVisible
            onTriggered: root.toggleColumnRequested("channels")
        }
        MichiMenuItem {
            text: qsTr("File Size")
            checkable: true
            checked: LibraryTrackColumnState.fileSizeVisible
            onTriggered: root.toggleColumnRequested("fileSize")
        }

        MichiMenuHeader { text: qsTr("METADATA") }
        MichiMenuItem {
            text: qsTr("Genre")
            checkable: true
            checked: LibraryTrackColumnState.genreVisible
            onTriggered: root.toggleColumnRequested("genre")
        }
        MichiMenuItem {
            text: qsTr("Composer")
            checkable: true
            checked: LibraryTrackColumnState.composerVisible
            onTriggered: root.toggleColumnRequested("composer")
        }
        MichiMenuItem {
            text: qsTr("Year")
            checkable: true
            checked: LibraryTrackColumnState.yearVisible
            onTriggered: root.toggleColumnRequested("year")
        }

        MichiMenuHeader { text: qsTr("TIME") }
        MichiMenuItem {
            text: qsTr("Duration")
            checkable: true
            checked: LibraryTrackColumnState.durationVisible
            onTriggered: root.toggleColumnRequested("duration")
        }

        MichiMenuHeader { text: qsTr("UTILITY") }
        MichiMenuItem {
            text: qsTr("Actions")
            checkable: true
            checked: LibraryTrackColumnState.actionsVisible
            onTriggered: root.toggleColumnRequested("actions")
        }
    }

    MichiSeparator { }

    MichiMenuItem {
        text: qsTr("Reset Column Widths")
        icon.name: "reset"
        onTriggered: root.resetWidthsRequested()
    }
    MichiMenuItem {
        text: qsTr("Restore Defaults")
        icon.name: "restore"
        onTriggered: root.restoreDefaultsRequested()
    }
}
