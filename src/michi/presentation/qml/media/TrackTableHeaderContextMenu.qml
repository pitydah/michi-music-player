import QtQuick
import "../controls"
import "../theme"

// LIB-A §11/12/14/16/17: menú contextual premium de la cabecera de tabla.
// DOS intents contextuales:
//   A) right-click sobre una CELL → contexto de la columna exacta
//      (sort explícito asc/desc, hide excepto Title, reset width);
//   B) right-click sobre la región vacía → configuración global de la
//      tabla (presets + columnas por grupo + reset widths/defaults).
// Todo con primitives Michi; nunca dead items.
MichiMenu {
    id: root

    property string targetColumn: ""       // "" = contexto global (B)
    property string targetLabel: ""
    property bool targetSortable: false
    property bool sortingEnabled: false
    // Autoridad global: la MISMA del singleton (read en open).
    signal sortAscendingRequested(string column)
    signal sortDescendingRequested(string column)
    signal hideColumnRequested(string column)
    signal resetWidthRequested(string column)
    signal presetRequested(string name)
    signal toggleColumnRequested(string column)
    signal resetWidthsRequested()
    signal restoreDefaultsRequested()

    // LIB-A §10: Title nunca se ofrece para ocultar.
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

    function columnVisible(column) {
        return LibraryTrackColumnState.isVisible(column)
    }

    // ── A) Contexto de CELL ────────────────────────────────────────────────
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
        visible: root.targetColumn !== ""
            && (root.targetSortable || root.targetColumn !== "title")
    }
    MichiMenuItem {
        text: root.targetColumn === "title"
            ? qsTr("Title (required)")
            : qsTr("Hide %1").arg(root.columnLabel(root.targetColumn))
        icon.name: root.targetColumn === "title" ? "lock" : "hide"
        visible: root.targetColumn !== "" && root.targetColumn !== "title"
        onTriggered: root.hideColumnRequested(root.targetColumn)
    }
    MichiMenuItem {
        text: qsTr("Reset %1 Width").arg(root.columnLabel(root.targetColumn))
        visible: root.targetColumn !== "" && root.targetColumn !== "actions"
        onTriggered: root.resetWidthRequested(root.targetColumn)
    }

    // ── B) Configuración global ────────────────────────────────────────────
    MichiSeparator { visible: root.targetColumn !== "" }

    MichiMenuItem {
        text: qsTr("COLUMN LAYOUT")
        enabled: false
    }
    MichiMenuItem {
        text: qsTr("Essential")
        checkable: true
        checked: LibraryTrackColumnState.currentPreset() === "essential"
        onTriggered: root.presetRequested("essential")
    }
    MichiMenuItem {
        text: qsTr("Audiophile")
        checkable: true
        checked: LibraryTrackColumnState.currentPreset() === "audiophile"
        onTriggered: root.presetRequested("audiophile")
    }
    MichiMenuItem {
        text: qsTr("Metadata")
        checkable: true
        checked: LibraryTrackColumnState.currentPreset() === "metadata"
        onTriggered: root.presetRequested("metadata")
    }
    MichiMenuItem {
        text: qsTr("Minimal")
        checkable: true
        checked: LibraryTrackColumnState.currentPreset() === "minimal"
        onTriggered: root.presetRequested("minimal")
    }

    MichiSeparator { }
    MichiMenuItem {
        text: qsTr("COLUMNS")
        enabled: false
    }
    // Identity (artwork) + Context + Audio + Metadata + Time — grupos.
    MichiMenuItem {
        text: qsTr("Artwork")
        checkable: true
        checked: root.columnVisible("artwork")
        onTriggered: root.toggleColumnRequested("artwork")
    }
    MichiMenuItem {
        text: qsTr("Title")
        enabled: false
        icon.name: "lock"
        visible: true
    }
    MichiMenuItem {
        text: qsTr("Artist")
        checkable: true
        checked: root.columnVisible("artist")
        onTriggered: root.toggleColumnRequested("artist")
    }
    MichiMenuItem {
        text: qsTr("Album")
        checkable: true
        checked: root.columnVisible("album")
        onTriggered: root.toggleColumnRequested("album")
    }
    MichiMenuItem {
        text: qsTr("Format")
        checkable: true
        checked: root.columnVisible("format")
        onTriggered: root.toggleColumnRequested("format")
    }
    MichiMenuItem {
        text: qsTr("Sample Rate")
        checkable: true
        checked: root.columnVisible("sampleRate")
        onTriggered: root.toggleColumnRequested("sampleRate")
    }
    MichiMenuItem {
        text: qsTr("Bit Depth")
        checkable: true
        checked: root.columnVisible("bitDepth")
        onTriggered: root.toggleColumnRequested("bitDepth")
    }
    MichiMenuItem {
        text: qsTr("DSD Rate")
        checkable: true
        checked: root.columnVisible("dsdRate")
        onTriggered: root.toggleColumnRequested("dsdRate")
    }
    MichiMenuItem {
        text: qsTr("Bitrate")
        checkable: true
        checked: root.columnVisible("bitrate")
        onTriggered: root.toggleColumnRequested("bitrate")
    }
    MichiMenuItem {
        text: qsTr("Channels")
        checkable: true
        checked: root.columnVisible("channels")
        onTriggered: root.toggleColumnRequested("channels")
    }
    MichiMenuItem {
        text: qsTr("File Size")
        checkable: true
        checked: root.columnVisible("fileSize")
        onTriggered: root.toggleColumnRequested("fileSize")
    }
    MichiMenuItem {
        text: qsTr("Genre")
        checkable: true
        checked: root.columnVisible("genre")
        onTriggered: root.toggleColumnRequested("genre")
    }
    MichiMenuItem {
        text: qsTr("Composer")
        checkable: true
        checked: root.columnVisible("composer")
        onTriggered: root.toggleColumnRequested("composer")
    }
    MichiMenuItem {
        text: qsTr("Year")
        checkable: true
        checked: root.columnVisible("year")
        onTriggered: root.toggleColumnRequested("year")
    }
    MichiMenuItem {
        text: qsTr("Duration")
        checkable: true
        checked: root.columnVisible("duration")
        onTriggered: root.toggleColumnRequested("duration")
    }
    MichiMenuItem {
        text: qsTr("Actions")
        checkable: true
        checked: root.columnVisible("actions")
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
