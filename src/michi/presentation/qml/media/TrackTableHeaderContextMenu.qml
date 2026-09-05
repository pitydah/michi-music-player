import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// LIB-A P2-C: menú contextual premium y COMPACTO de la cabecera.
// Dos intents (cell vs región global) con un menú principal reducido y un
// popup dedicado de personalización (nunca un menú gigante que exceda la
// altura de la ventana).
MichiMenu {
    id: root

    property string targetColumn: ""       // "" = contexto global (B)
    property string targetLabel: ""
    property bool targetSortable: false
    signal sortAscendingRequested(string column)
    signal sortDescendingRequested(string column)
    signal hideColumnRequested(string column)
    signal resetWidthRequested(string column)
    signal presetRequested(string name)
    signal toggleColumnRequested(string column)
    signal resetWidthsRequested()
    signal restoreDefaultsRequested()

    function columnLabel(column) {
        var labels = {
            artwork: qsTr("Artwork"), title: qsTr("Title"),
            artist: qsTr("Artist"), album: qsTr("Album"),
            format: qsTr("Format"), sampleRate: qsTr("Sample Rate"),
            bitDepth: qsTr("Bit Depth"), dsdRate: qsTr("DSD Rate"),
            bitrate: qsTr("Bitrate"), channels: qsTr("Channels"),
            fileSize: qsTr("File Size"), genre: qsTr("Genre"),
            composer: qsTr("Composer"), year: qsTr("Year"),
            duration: qsTr("Duration"), actions: qsTr("Actions")
        }
        return labels[column] !== undefined ? labels[column] : column
    }

    function openCustomize() {
        root.close()
        customizePopup.open()
    }

    function applyPreset(name) {
        LibraryTrackColumnState.applyPreset(name)
        root.presetRequested(name)
    }

    // ── A) Contexto de CELL (compacto) ────────────────────────────────────
    MichiMenuItem {
        text: qsTr("TRACK TABLE")
        enabled: false
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
    MichiSeparator {
        visible: root.targetColumn !== "" && root.targetColumn !== "title"
    }
    MichiMenuItem {
        text: qsTr("Hide %1").arg(root.columnLabel(root.targetColumn))
        visible: root.targetColumn !== "" && root.targetColumn !== "title"
        onTriggered: root.hideColumnRequested(root.targetColumn)
    }
    MichiMenuItem {
        text: qsTr("Reset %1 Width").arg(root.columnLabel(root.targetColumn))
        visible: root.targetColumn !== "" && root.targetColumn !== "actions"
        onTriggered: root.resetWidthRequested(root.targetColumn)
    }

    // ── B) Configuración global compacta ──────────────────────────────────
    MichiSeparator { visible: root.targetColumn !== "" }

    MichiMenuItem {
        text: qsTr("Customize Columns…")
        icon.name: "sliders"
        onTriggered: root.openCustomize()
    }
    MichiMenuItem {
        text: qsTr("Reset Column Widths")
        visible: root.targetColumn === ""
        onTriggered: root.resetWidthsRequested()
    }
    MichiMenuItem {
        text: qsTr("Restore Defaults")
        visible: root.targetColumn === ""
        onTriggered: root.restoreDefaultsRequested()
    }

    // Popup de personalización (jerarquía por grupos; altura acotada).
    // Vive como hermano del menú para reusar el ancla; MichiMenu con
    // scroll si el contenido excede la altura disponible.
    MichiMenu {
        id: customizePopup

        function rebuild() {
            // Lazy: los checks se leen al abrir.
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

        MichiMenuItem { text: qsTr("CUSTOMIZE COLUMNS"); enabled: false }
        MichiMenuItem {
            id: presetEssential
            text: qsTr("Essential")
            checkable: true
            onTriggered: root.applyPreset("essential")
        }
        MichiMenuItem {
            id: presetAudiophile
            text: qsTr("Audiophile")
            checkable: true
            onTriggered: root.applyPreset("audiophile")
        }
        MichiMenuItem {
            id: presetMetadata
            text: qsTr("Metadata")
            checkable: true
            onTriggered: root.applyPreset("metadata")
        }
        MichiMenuItem {
            id: presetMinimal
            text: qsTr("Minimal")
            checkable: true
            onTriggered: root.applyPreset("minimal")
        }
        MichiSeparator { }
        MichiMenuItem { text: qsTr("IDENTITY"); enabled: false }
        MichiMenuItem {
            text: qsTr("Artwork")
            checkable: true
            checked: LibraryTrackColumnState.artworkVisible
            onTriggered: root.toggleColumnRequested("artwork")
        }
        MichiMenuItem {
            text: qsTr("Title (required)")
            enabled: false
            icon.name: "lock"
        }
        MichiSeparator { }
        MichiMenuItem { text: qsTr("MUSICAL CONTEXT"); enabled: false }
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
        MichiSeparator { }
        MichiMenuItem { text: qsTr("AUDIO"); enabled: false }
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
        MichiSeparator { }
        MichiMenuItem { text: qsTr("METADATA"); enabled: false }
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
        MichiSeparator { }
        MichiMenuItem { text: qsTr("TIME"); enabled: false }
        MichiMenuItem {
            text: qsTr("Duration")
            checkable: true
            checked: LibraryTrackColumnState.durationVisible
            onTriggered: root.toggleColumnRequested("duration")
        }
        MichiSeparator { }
        MichiMenuItem { text: qsTr("UTILITY"); enabled: false }
        MichiMenuItem {
            text: qsTr("Actions")
            checkable: true
            checked: LibraryTrackColumnState.actionsVisible
            onTriggered: root.toggleColumnRequested("actions")
        }
        MichiSeparator { }
        MichiMenuItem {
            text: qsTr("Reset Column Widths")
            onTriggered: root.resetWidthsRequested()
        }
        MichiMenuItem {
            text: qsTr("Restore Defaults")
            onTriggered: root.restoreDefaultsRequested()
        }
    }
}
