import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property int trackId: 0
    property string trackTitle: ""
    property string trackArtist: ""
    property string trackAlbum: ""
    property int trackDuration: 0
    property string trackFormat: ""
    property int trackYear: 0
    property string trackGenre: ""
    property int trackNumber: 0
    property bool trackFavorite: false
    property bool trackMissing: false
    property int trackQuality: 0
    property bool isSelected: false
    property bool isShiftPressed: false
    property int lastClickedIndex: -1
    property int rowIndex: 0

    signal playClicked()
    signal doubleClicked()
    signal rightClicked(int mx, int my)
    signal selectionToggled(int id, bool ctrl, bool shift)

    height: 36
    Accessible.role: Accessible.ListItem
    Accessible.name: trackTitle + " - " + trackArtist
    Accessible.onPressAction: root.playClicked()

    Rectangle {
        anchors.fill: parent
        color: root.isSelected ? MichiTheme.colors.accentSurface :
               mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

        Rectangle {
            anchors.left: parent.left
            width: 3; height: parent.height
            color: MichiTheme.colors.accentBlue
            visible: root.isSelected
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.sm
        spacing: 0

        TrackStatusIndicators {
            favorite: root.trackFavorite
            missing: root.trackMissing
            width: 20
        }

        Text {
            text: root.trackNumber > 0 ? root.trackNumber : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            width: 30
            horizontalAlignment: Text.AlignRight
        }

        Text {
            text: root.trackTitle || ""
            color: root.isSelected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: root.isSelected ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
            Layout.fillWidth: true
            elide: Text.ElideRight
            leftPadding: MichiTheme.spacing.sm
        }

        Text {
            text: root.trackArtist || ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            Layout.preferredWidth: 160
            elide: Text.ElideRight
        }

        Text {
            text: root.trackAlbum || ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            Layout.preferredWidth: 160
            elide: Text.ElideRight
        }

        TrackQualityBadge {
            format: root.trackFormat
            bitDepth: root.trackQuality
            width: 40
        }

        Text {
            text: root.trackYear > 0 ? root.trackYear : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            width: 40
            horizontalAlignment: Text.AlignRight
        }

        Text {
            text: formatDuration(root.trackDuration)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            width: 48
            horizontalAlignment: Text.AlignRight
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                root.rightClicked(mouse.x, mouse.y)
            } else {
                var ctrl = mouse.modifiers & Qt.ControlModifier
                var shift = mouse.modifiers & Qt.ShiftModifier
                root.selectionToggled(root.trackId, ctrl, shift)
            }
        }

        onDoubleClicked: root.playClicked()
    }

    function formatDuration(secs) {
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
