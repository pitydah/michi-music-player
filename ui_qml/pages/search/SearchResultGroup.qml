import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Result Group"
    objectName: "searchResultGroup"
    focus: true
    id: root

    property string sectionTitle: ""
    property var items: []
    property var bridge: null

    signal itemClicked(string type, string id, string title)

    implicitHeight: childrenRect.height

    Column {
        width: parent.width; spacing: MichiTheme.spacing.sm

        SectionHeader { text: root.sectionTitle; width: parent.width }

        Repeater {
            model: root.items

            Rectangle {
                width: parent.width; height: 40
                color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                radius: MichiTheme.radius.sm

                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                    Text {
                        width: parent.width * 0.45; text: modelData.title || ""
                        color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.35; text: modelData.subtitle || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 24; text: "▶"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                        visible: modelData.type === "track"
                        Accessible.role: Accessible.Button
                        Accessible.name: "Reproducir"
                        Accessible.description: "Reproducir esta canción"
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.itemClicked(modelData.type || "", modelData.id || "", modelData.title || "")
                        }
                    }
                }

                MouseArea {
                    id: mouseArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.itemClicked(modelData.type || "", modelData.id || "", modelData.title || "")
                }
            }
        }
    }
}
