import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property var cpb: typeof commandPaletteBridge !== "undefined" ? commandPaletteBridge : null
    property bool open: false
    property var _results: []

    visible: open

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.03, 0.05, 0.70)
        z: 9998

        MouseArea { anchors.fill: parent; onClicked: root.open = false }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 400; height: 320
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCardElevated
        z: 9999

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            TextField {
                id: searchField
                width: parent.width
                placeholderText: "Buscar comando..."
                font.pixelSize: MichiTheme.typography.bodySize
                onTextChanged: {
                    if (root.cpb) root._results = root.cpb.searchCommands(text)
                }
                Keys.onEscapePressed: root.open = false
                Keys.onReturnPressed: executeSelected()
            }

            ListView {
                width: parent.width
                height: parent.height - searchField.height - MichiTheme.spacing.lg
                model: root._results
                clip: true

                delegate: Rectangle {
                    width: parent.width; height: 32; color: "transparent"
                    Text {
                        anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root._execute(modelData.id || "")
                        }
                    }
                }
            }
        }
    }

    function executeSelected() {
        if (root._results && root._results.length > 0) {
            root._execute(root._results[0].id || "")
        }
    }

    function _execute(id) {
        if (root.cpb) {
            root.cpb.executeCommand(id)
        }
        root.open = false
    }
}
