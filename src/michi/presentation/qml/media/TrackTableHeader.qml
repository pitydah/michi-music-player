import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root

    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showArtwork: true
    property int actionColumnWidth: 0

    // Matches the minimum TrackRow height (controlMedium) so the header
    // never reads shorter than its rows.
    implicitHeight: MichiMetrics.controlMedium
    color: MichiSemanticColors.controlSurface
    radius: MichiRadius.sm
    border.width: 1
    border.color: MichiSemanticColors.borderSubtle
    z: 2

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        MichiText {
            Layout.preferredWidth: 20
            text: qsTr("#")
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
            horizontalAlignment: Text.AlignHCenter
        }
        Item {
            visible: root.showArtwork
            Layout.preferredWidth: MichiThemeState.density === "comfortable" ? 36 : 30
            Layout.preferredHeight: Layout.preferredWidth
        }
        MichiText {
            Layout.fillWidth: true
            text: qsTr("TITLE")
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
        MichiText {
            visible: root.showArtistColumn
            Layout.preferredWidth: 160
            text: qsTr("ARTIST")
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
        MichiText {
            visible: root.showAlbumColumn && !MichiThemeState.precisionMode
            Layout.preferredWidth: 180
            text: qsTr("ALBUM")
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
        MichiText {
            visible: MichiThemeState.precisionMode
            Layout.preferredWidth: 150
            text: qsTr("QUALITY")
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
        Item {
            Layout.preferredWidth: 48
            Layout.fillHeight: true
            Accessible.name: qsTr("Duration")
            MichiIcon {
                anchors.centerIn: parent
                width: MichiMetrics.iconSmall
                height: width
                name: "history"
                iconColor: MichiPalette.textMuted
            }
        }
        Item {
            visible: root.actionColumnWidth > 0
            Layout.preferredWidth: root.actionColumnWidth
            Layout.fillHeight: true
        }
    }
}
