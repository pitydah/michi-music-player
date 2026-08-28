import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiDialog {
    id: root

    property var track: null
    readonly property var propertyRows: track ? [
        [qsTr("Title"), track.title || track.displayName || ""],
        [qsTr("Artist"), track.artist || ""],
        [qsTr("Album"), track.album || ""],
        [qsTr("Album artist"), track.albumArtist || qsTr("Unknown")],
        [qsTr("Track"), track.trackNumber > 0
            ? String(track.trackNumber) : qsTr("Unknown")],
        [qsTr("Disc"), track.discNumber > 0
            ? String(track.discNumber) : qsTr("Unknown")],
        [qsTr("Genre"), track.genre || qsTr("Unknown")],
        [qsTr("Composer"), track.composer || qsTr("Unknown")],
        [qsTr("Year"), track.year > 0 ? String(track.year) : qsTr("Unknown")],
        [qsTr("Format"), track.formatLabel || "UNKNOWN"],
        [qsTr("Codec"), track.codec || qsTr("Unknown")],
        [qsTr("Container"), track.container || qsTr("Unknown")],
        [qsTr("Sample rate"), track.sampleRateHz > 0
            ? (track.sampleRateHz / 1000) + " kHz" : qsTr("Unknown")],
        [qsTr("Bit depth"), track.bitDepth > 0
            ? track.bitDepth + "-bit" : qsTr("Unknown")],
        [qsTr("DSD rate"), track.dsdRate || qsTr("Not applicable")],
        [qsTr("Bitrate"), track.bitrateBps > 0
            ? Math.round(track.bitrateBps / 1000) + " kbps" : qsTr("Unknown")],
        [qsTr("Channels"), track.channels > 0
            ? String(track.channels) : qsTr("Unknown")],
        [qsTr("Duration"), track.durationMs > 0
            ? MichiFormat.formatDuration(track.durationMs) : qsTr("Unknown")],
        [qsTr("File size"), track.fileSize > 0
            ? MichiFormat.formatFileSize(track.fileSize) : qsTr("Unknown")],
        [qsTr("Location"), track.path || ""]
    ] : []

    title: qsTr("Track properties")
    width: 560
    height: 620
    standardButtons: Dialog.Close

    function inspect(trackRow) {
        track = trackRow
        open()
    }

    contentItem: ListView {
        model: root.propertyRows
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: MichiScrollBar { }

        delegate: RowLayout {
            required property var modelData
            width: ListView.view.width
            spacing: MichiSpacing.lg
            MichiText {
                Layout.preferredWidth: 130
                text: modelData[0]
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            MichiText {
                Layout.fillWidth: true
                text: modelData[1]
                role: "body"
                wrapMode: Text.Wrap
            }
        }
    }
}
