import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

// PlaylistColumnHeader — the quiet 10px uppercase column labels of the
// editorial track table. Used twice: in-flow below the hero (scrolls with
// it) and as the sticky overlay once the hero scrolls away.
Item {
    id: root

    property bool showArtist: true
    property bool showAlbum: true
    property bool showFormat: false

    implicitHeight: 34

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.md
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        Item { Layout.preferredWidth: 36 }   // track number
        Item { Layout.preferredWidth: 40 }   // artwork

        MichiText {
            Layout.preferredWidth: root.width * 0.34
            Layout.minimumWidth: 120
            text: qsTr("TITLE")
            role: "micro"
            color: MichiPalette.textSecondary
            opacity: 0.58
            font.weight: Font.DemiBold
        }
        MichiText {
            visible: root.showArtist
            Layout.preferredWidth: root.width * 0.21
            Layout.minimumWidth: 90
            Layout.maximumWidth: 240
            text: qsTr("ARTIST")
            role: "micro"
            color: MichiPalette.textSecondary
            opacity: 0.58
            font.weight: Font.DemiBold
        }
        MichiText {
            visible: root.showAlbum
            Layout.preferredWidth: root.width * 0.21
            Layout.minimumWidth: 90
            Layout.maximumWidth: 240
            text: qsTr("ALBUM")
            role: "micro"
            color: MichiPalette.textSecondary
            opacity: 0.58
            font.weight: Font.DemiBold
        }
        MichiText {
            visible: root.showFormat
            Layout.preferredWidth: LibraryTrackColumnState.formatWidth
            text: qsTr("FORMAT")
            role: "micro"
            color: MichiPalette.textSecondary
            opacity: 0.58
            font.weight: Font.DemiBold
        }
        MichiText {
            Layout.preferredWidth: 54
            text: qsTr("TIME")
            role: "micro"
            color: MichiPalette.textSecondary
            opacity: 0.58
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignRight
        }
        Item { Layout.preferredWidth: 76 }   // two 32px actions + 12px gap
    }
}
