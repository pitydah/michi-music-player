import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string rowType: ""
    property string rowId: ""
    property string rowTitle: ""
    property string rowSubtitle: ""
    property var bridge: null

    signal clicked()
    signal playRequested()

    implicitHeight: 44

    objectName: "searchResultRow_" + rowType + "_" + (rowId ? rowId : "unknown")

    Accessible.role: Accessible.ListItem
    Accessible.name: rowTitle + " - " + rowSubtitle
    Accessible.description: "Tipo: " + rowType + ". Presiona Enter para abrir"

    function getThumbnailText() {
        switch (root.rowType) {
            case "track": return "\u266A"
            case "album": return "\u25C9"
            case "artist": return "\u266B"
            case "playlist": return "\u2630"
            case "folder": return "\u25A0"
            case "genre": return "\u266C"
            case "radio": return "\u25E2"
            case "device": return "\u25D8"
            case "server": return "\u25CB"
            case "action": return "\u2192"
            case "setting": return "\u2699"
            default: return "\u25CF"
        }
    }

    function getTypeLabel() {
        switch (root.rowType) {
            case "track": return "Canción"
            case "album": return "Álbum"
            case "artist": return "Artista"
            case "playlist": return "Lista"
            case "folder": return "Carpeta"
            case "genre": return "Género"
            case "radio": return "Radio"
            case "device": return "Dispositivo"
            case "server": return "Servidor"
            case "action": return "Acción"
            case "setting": return "Ajuste"
            default: return ""
        }
    }

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus : "transparent"
        border.width: root.activeFocus ? MichiTheme.borderWidthFocus : 0

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.sm

            Rectangle {
                width: 36
                height: 36
                radius: MichiTheme.radiusSm
                anchors.verticalCenter: parent.verticalCenter
                color: MichiTheme.colors.accentFaint

                Text {
                    anchors.centerIn: parent
                    text: root.getThumbnailText()
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Accessible.role: Accessible.Graphic
                Accessible.name: root.getTypeLabel()
            }

            Column {
                width: parent.width - 100
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                Text {
                    text: root.rowTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width
                }

                Text {
                    text: root.rowSubtitle
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    width: parent.width
                    visible: text !== ""
                }
            }

            StatusBadge {
                id: typeBadge
                text: root.getTypeLabel()
                kind: "info"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.getTypeLabel() !== ""
                Accessible.role: Accessible.StaticText
                Accessible.name: "Tipo: " + root.getTypeLabel()
            }

            Text {
                text: "\u25B6"
                color: MichiTheme.colors.accent
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: MichiTheme.typography.bodySize
                width: 20
                visible: root.rowType === "track"

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.playRequested()
                    Accessible.role: Accessible.Button
                    Accessible.name: "Reproducir " + root.rowTitle
                }
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
            onDoubleClicked: root.playRequested()
        }

        Keys.onReturnPressed: root.clicked()
        Keys.onSpacePressed: root.clicked()
    }
}
