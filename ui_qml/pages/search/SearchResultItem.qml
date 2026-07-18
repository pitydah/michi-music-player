import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Result Item"
    objectName: "searchResultItem"
    focus: true
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

    implicitHeight: 44

    Rectangle {
        anchors.fill: parent; radius: MichiTheme.radius.sm
        color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

        Row {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

            Rectangle {
                width: 36; height: 36; radius: MichiTheme.radius.sm; anchors.verticalCenter: parent.verticalCenter
                color: MichiTheme.colors.accentFaint
                Text {
                    anchors.centerIn: parent
                    text: {
                        if (root.resultType === "track") return "T"
                        if (root.resultType === "album") return "A"
                        if (root.resultType === "artist") return "Ar"
                        if (root.resultType === "playlist") return "P"
                        return "?"
                    }
                    color: MichiTheme.colors.accent; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            Column {
                width: parent.width - 80; anchors.verticalCenter: parent.verticalCenter; spacing: 1
                Text {
                    text: root.resultTitle; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight; width: parent.width
                }
                Text {
                    text: root.resultSubtitle; color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; width: parent.width
                    visible: text !== ""
                }
            }

            Text {
                text: qsTr("▶"); color: MichiTheme.colors.accent; anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: MichiTheme.typography.bodySize; width: 24
                visible: root.resultType === "track"
                Accessible.role: Accessible.Button
                Accessible.name: "Reproducir"
                Accessible.description: "Reproducir esta canción"
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: root.playRequested()
                }
            }
        }

        MouseArea {
            id: mouseArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
        }
    }
}
