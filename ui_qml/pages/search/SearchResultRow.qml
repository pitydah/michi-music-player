import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string resultType: ""
    property string resultId: ""
    property string resultTitle: ""
    property string resultSubtitle: ""
    property string resultSection: ""
    property real resultScore: 0.0
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    property string rowType: ""
    property string rowId: ""
    property string rowTitle: ""
    property string rowSubtitle: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    property var bridge: null

    signal clicked()
    signal playRequested()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    signal activateRequested()
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus : "transparent"
        border.width: root.activeFocus ? MichiTheme.borderWidthFocus : 0
=======
        border.width: itemFocus.active ? 1 : 0
        border.color: MichiTheme.colors.borderFocus

        Rectangle {
            id: itemFocus
            property bool active: mouseArea.containsMouse || keyboardFocus.active
            anchors.fill: parent
            radius: MichiTheme.radiusSm
            color: "transparent"
            border.width: active ? MichiTheme.borderWidthFocus : 0
            border.color: MichiTheme.colors.borderFocus
        }
=======

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
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.sm

            Rectangle {
                width: 36
                height: 36
                radius: MichiTheme.radiusSm
                anchors.verticalCenter: parent.verticalCenter
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                color: MichiTheme.colors.accentFaint
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                color: MichiTheme.colors.accentSurface
>>>>>>> Stashed changes

                Text {
                    anchors.centerIn: parent
                    text: root.getThumbnailText()
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                }
<<<<<<< Updated upstream
<<<<<<< Updated upstream

                Accessible.role: Accessible.Graphic
                Accessible.name: root.getTypeLabel()
=======
=======
>>>>>>> Stashed changes
=======
                color: MichiTheme.colors.accentFaint

                Text {
                    anchors.centerIn: parent
                    text: root.getThumbnailText()
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Accessible.role: Accessible.Graphic
                Accessible.name: root.getTypeLabel()
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            }

            Column {
                width: parent.width - 100
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                Text {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                    text: root.rowTitle
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    text: root.resultTitle
=======
                    text: root.rowTitle
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width
                }

                Text {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                    text: root.rowSubtitle
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    text: root.resultSubtitle
=======
                    text: root.rowSubtitle
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    width: parent.width
                    visible: text !== ""
                }
            }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes
            StatusBadge {
                id: typeBadge
                text: root.getTypeLabel()
                kind: "info"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.getTypeLabel() !== ""
                Accessible.role: Accessible.StaticText
                Accessible.name: "Tipo: " + root.getTypeLabel()
            }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            Text {
                text: "\u25B6"
                color: MichiTheme.colors.accent
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: MichiTheme.typography.bodySize
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                width: 20
                visible: root.rowType === "track"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                width: 24
                visible: root.resultType === "track"
=======
                width: 20
                visible: root.rowType === "track"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.playRequested()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                    Accessible.role: Accessible.Button
                    Accessible.name: "Reproducir " + root.rowTitle
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
                    Accessible.role: Accessible.Button
                    Accessible.name: "Reproducir " + root.rowTitle
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                }
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            onDoubleClicked: root.playRequested()
        }

        Keys.onReturnPressed: root.clicked()
        Keys.onSpacePressed: root.clicked()
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        }

        Keys.onReturnPressed: {
            root.activateRequested()
        }
        Keys.onEnterPressed: {
            root.activateRequested()
        }

        focus: true
        activeFocusOnTab: false
=======
            onDoubleClicked: root.playRequested()
        }

        Keys.onReturnPressed: root.clicked()
        Keys.onSpacePressed: root.clicked()
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    }
}
