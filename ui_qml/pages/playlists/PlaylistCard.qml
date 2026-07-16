import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Playlist Card"
    objectName: "playlistCard"
    focus: true
    id: root

    property string playlistTitle: ""
    property int trackCount: 0
    property string duration: ""
    property string coverKey: ""
    property bool selected: false
    property bool showSelection: false

    signal clicked()
    signal contextMenuRequested(string action)

    implicitWidth: 200
    implicitHeight: 240


    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        hovered: mouseArea.containsMouse
        interactive: true

        Rectangle {
            anchors.fill: parent
            radius: MichiTheme.radiusMd
            color: root.selected ? MichiTheme.colors.accentSurface : "transparent"
            visible: root.showSelection || root.selected
            border.color: root.selected ? MichiTheme.colors.accent : "transparent"
            border.width: root.selected ? 2 : 0
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: root.clicked()
            onPressAndHold: contextMenu.popup()
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            CoverImage {
                width: parent.width
                height: width
                coverRadius: MichiTheme.radiusSm
                coverKey: root.coverKey || root.playlistTitle || "PL"
            }

            Text {
                text: root.playlistTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width
            }
            Text {
                text: root.trackCount > 0 ? root.trackCount + " canciones" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }
            Text {
                text: root.duration
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.duration !== ""
            }
        }
    }

    Menu {
        Accessible.role: Accessible.PopupMenu

        Accessible.name: "Menu"

            Accessible.role: Accessible.MenuItem

        id: contextMenu
        activeFocusOnTab: true

        MenuItem {
            Accessible.role: Accessible.MenuItem

            Accessible.name: "MenuItem"

            activeFocusOnTab: true

            text: "Reproducir"
            onTriggered: root.contextMenuRequested("shuffle")
            Accessible.role: Accessible.MenuItem

            Accessible.name: "MenuItem"

            activeFocusOnTab: true

        }
        MenuItem {
            text: "Duplicar"
            onTriggered: root.contextMenuRequested("duplicate")
        }
        MenuSeparator {}
        MenuItem {
            text: "Eliminar"
            onTriggered: root.contextMenuRequested("delete")
        }
    }

    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()
    Keys.onMenuPressed: contextMenu.popup()
}
