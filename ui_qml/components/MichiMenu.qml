import QtQuick
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: root.controlObjectName

    property bool open: false
    property int currentIndex: -1
    property var model: []
    property string accessibleName: "Men\u00FA"
    property string accessibleDescription: ""

    signal selected(int index, var item)
    signal closed()

    implicitWidth: 200
    implicitHeight: root.open ? Math.min(root.model.length * rowHeight + MichiTheme.spacing.xs * 2, 400) : 0

    Accessible.role: Accessible.Menu
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    readonly property int rowHeight: MichiTheme.density.regular

    visible: root.open
    clip: true

    function close() {
        root.open = false
        root.closed()
    }

    function _selectCurrent() {
        if (root.currentIndex >= 0 && root.currentIndex < root.model.length) {
            root.selected(root.currentIndex, root.model[root.currentIndex])
            root.close()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        layer.enabled: false

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xs
            spacing: MichiTheme.spacing.xxs

            Repeater {
                model: root.model

                Item {
                    width: parent.width
                    implicitHeight: root.rowHeight
                    property bool isSelected: index === root.currentIndex
                    property bool isHovered: itemMa.containsMouse

                    Rectangle {
                        anchors.fill: parent
                        radius: MichiTheme.radius.xs
                        color: isSelected ? MichiTheme.colors.accentSelection
                             : isHovered ? MichiTheme.colors.surfaceHover : "transparent"
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.verticalCenter: parent.verticalCenter
                        text: typeof modelData === "string" ? modelData : (modelData.text || modelData)
                        color: isSelected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: isSelected ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: itemMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.currentIndex = index
                            root._selectCurrent()
                        }
                    }
                }
            }
        }
    }

    Keys.onUpPressed: function(event) {
        root.currentIndex = Math.max(0, root.currentIndex - 1)
        event.accepted = true
    }

    Keys.onDownPressed: function(event) {
        root.currentIndex = Math.min(root.model.length - 1, root.currentIndex + 1)
        event.accepted = true
    }

    Keys.onReturnPressed: function(event) {
        root._selectCurrent()
        event.accepted = true
    }

    Keys.onEnterPressed: function(event) {
        root._selectCurrent()
        event.accepted = true
    }

    Keys.onEscapePressed: function(event) {
        root.close()
        event.accepted = true
    }
}
