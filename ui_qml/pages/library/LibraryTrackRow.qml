import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Track Row"
    objectName: "libraryTrackRow"
    focus: true
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
    MichiResponsive { id: responsive; availableWidth: root.width }

    signal playClicked()
    signal doubleClicked()
    signal rightClicked(int mx, int my)
    signal selectionToggled(int id, bool ctrl, bool shift)

    height: MichiTheme.rowHeightComfortable
    activeFocusOnTab: true
    Accessible.onPressAction: root.playClicked()

    Rectangle {
        anchors.fill: parent
        color: root.isSelected ? MichiTheme.colors.accentSelection
               : mouseArea.pressed ? MichiTheme.colors.surfacePressed
               : mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
        border.width: root.activeFocus ? MichiTheme.focusWidth : 0
        border.color: MichiTheme.colors.borderFocus

        Rectangle {
            anchors.left: parent.left
            width: 3; height: parent.height
            color: MichiTheme.colors.accentPrimary
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
            color: root.isSelected ? MichiTheme.colors.accentPrimary : MichiTheme.colors.textPrimary
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
            Layout.preferredWidth: responsive.compact ? 120 : 160
            elide: Text.ElideRight
        }

        Text {
            text: root.trackAlbum || ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            Layout.preferredWidth: responsive.compact ? 120 : 160
            elide: Text.ElideRight
        }

        TrackQualityBadge {
            format: root.trackFormat
            bitDepth: root.trackQuality
            width: 40
            visible: !responsive.compact
        }

        Text {
            text: root.trackYear > 0 ? root.trackYear : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            width: 40
            visible: !responsive.compact
            horizontalAlignment: Text.AlignRight
        }

        Text {
            text: formatDuration(root.trackDuration)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            width: 48
            visible: !responsive.compact
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

    Keys.onReturnPressed: root.playClicked()
    Keys.onSpacePressed: root.selectionToggled(root.trackId, false, false)

    function formatDuration(secs) {
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
