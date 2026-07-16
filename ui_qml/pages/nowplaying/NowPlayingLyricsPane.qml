import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Lyrics Pane"
    objectName: "nowPlayingLyricsPane"
    focus: true
    property var ps: null

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Text {
            text: "Letra"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: "Letra no disponible"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            font.italic: true
            wrapMode: Text.WordWrap
        }
    }
}
