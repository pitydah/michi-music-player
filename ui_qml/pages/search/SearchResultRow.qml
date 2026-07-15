import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string resultType: ""
    property string resultId: ""
    property string resultTitle: ""
    property string resultSubtitle: ""
    property string resultSection: ""
    property real resultScore: 0.0
    property var bridge: null

    signal clicked()
    signal playRequested()
    signal activateRequested()

    implicitHeight: 44
    objectName: "searchResultRow"

    Accessible.role: Accessible.ListItem
    Accessible.name: resultTitle + (resultSubtitle !== "" ? " - " + resultSubtitle : "")
    Accessible.description: "Tipo: " + resultType + (resultScore > 0 ? ", relevancia: " + Math.round(resultScore * 100) + "%" : "")

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
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

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.sm

            Rectangle {
                width: 36
                height: 36
                radius: MichiTheme.radiusSm
                anchors.verticalCenter: parent.verticalCenter
                color: MichiTheme.colors.accentSurface

                Text {
                    anchors.centerIn: parent
                    text: {
                        switch (root.resultType) {
                            case "track": return "T"
                            case "album": return "A"
                            case "artist": return "Ar"
                            case "playlist": return "P"
                            case "folder": return "F"
                            case "genre": return "G"
                            case "radio": return "R"
                            case "device": return "D"
                            case "server": return "S"
                            case "action": return "!"
                            case "setting": return "\u2699"
                            default: return "?"
                        }
                    }
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightBold
                }
            }

            Column {
                width: parent.width - 100
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                Text {
                    text: root.resultTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width
                }

                Text {
                    text: root.resultSubtitle
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    width: parent.width
                    visible: text !== ""
                }
            }

            Text {
                text: "\u25B6"
                color: MichiTheme.colors.accent
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: MichiTheme.typography.bodySize
                width: 24
                visible: root.resultType === "track"

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.playRequested()
                }
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
        }

        Keys.onReturnPressed: {
            root.activateRequested()
        }
        Keys.onEnterPressed: {
            root.activateRequested()
        }

        focus: true
        activeFocusOnTab: false
    }
}
