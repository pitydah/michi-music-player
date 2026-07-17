import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Composers"
    objectName: "composersPage"
    focus: true
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _composers: []

    signal composerSelected(string composer)

    function reload() {
        if (root.lib && root.lib.getComposers) {
            root._composers = root.lib.getComposers() || []
        }
    }

    Component.onCompleted: reload()

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: MichiTheme.colors.surfaceCard

            Text {
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: MichiTheme.spacing.md
                text: "Compositores"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }
        }

        ListView {
            Accessible.role: Accessible.List

            Accessible.name: "Lista de compositores"

            activeFocusOnTab: true

            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._composers
            clip: true; spacing: MichiTheme.spacing.xs

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: parent.width; height: 40
                Rectangle {
                    anchors.fill: parent; color: mouse.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm
                        Text {
                            text: typeof modelData === "object" ? (modelData.name || modelData.composer) : modelData
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }
                        Text {
                            text: typeof modelData === "object" && modelData.count ? modelData.count + " canciones" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                    MouseArea {
                        id: mouse
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.composerSelected(typeof modelData === "object" ? modelData.name || modelData.composer : modelData)
                    }
                }
            }
        }
    }
}
