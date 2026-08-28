import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiDialog {
    id: root

    property var album: null
    readonly property var propertyRows: album ? [
        [qsTr("Title"), album.title || ""],
        [qsTr("Artist"), album.artist || ""],
        [qsTr("Year"), album.year > 0 ? String(album.year) : qsTr("Unknown")],
        [qsTr("Genre"), (album.genres || []).join(" · ") || qsTr("Unknown")],
        [qsTr("Track count"), String(album.trackCount || 0)],
        [qsTr("Duration"), MichiFormat.formatDuration(album.durationMs || 0)],
        [qsTr("Formats"), (album.formatsPresent || []).join(", ") || qsTr("Unknown")],
        [qsTr("Sample rates"), (album.sampleRatesPresent || []).map(
            value => (value / 1000) + " kHz").join(", ") || qsTr("Unknown")],
        [qsTr("Bit depths"), (album.bitDepthsPresent || []).map(
            value => value + "-bit").join(", ") || qsTr("Unknown")],
        [qsTr("DSD rates"), (album.dsdRatesPresent || []).join(", ")
            || qsTr("Not applicable")]
    ] : []

    title: qsTr("Album properties")
    width: 560
    height: 540
    standardButtons: Dialog.Close

    function inspect(albumRow) {
        album = albumRow
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
