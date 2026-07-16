import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    objectName: "michiComboBox"

    property var model: []
    property int currentIndex: -1
    property string currentText: ""
    property string placeholderText: "Seleccionar..."
    property bool loading: false
    property bool popupOpen: false
    property string accessibleName: root.placeholderText
    property string accessibleDescription: ""

    signal activated(int index)
    signal currentIndexChanged()

    implicitHeight: MichiTheme.minimumInteractiveSize
    implicitWidth: 200

    Accessible.role: Accessible.ComboBox
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    onCurrentIndexChanged: {
        if (root.currentIndex >= 0 && root.currentIndex < root.model.length)
            root.currentText = root.model[root.currentIndex]
        else
            root.currentText = ""
    }

    Rectangle {
        id: trigger
        anchors.fill: parent
        radius: MichiTheme.radius.sm
        color: root.loading ? MichiTheme.colors.surfaceDisabled : MichiTheme.colors.surfaceInput
        border.width: root.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

        Text {
            anchors.left: parent.left
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.right: arrow.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.currentText !== "" ? root.currentText : root.placeholderText
            color: root.currentText !== "" ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            elide: Text.ElideRight
        }

        Text {
            id: arrow
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.verticalCenter: parent.verticalCenter
            text: "\u25BE"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
        }

        MouseArea {
            anchors.fill: parent
            enabled: !root.loading
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.forceActiveFocus()
                root.popupOpen = !root.popupOpen
            }
        }
    }

    Rectangle {
        id: dropdown
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: trigger.bottom
        anchors.topMargin: MichiTheme.spacing.xxs
        visible: root.popupOpen && !root.loading
        radius: MichiTheme.radius.sm
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        z: 1000

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xxs
            spacing: MichiTheme.spacing.xxs

            Repeater {
                model: root.model

                Item {
                    width: parent.width
                    implicitHeight: MichiTheme.rowHeightCompact
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
                        text: modelData
                        color: root.currentIndex === index ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: root.currentIndex === index ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: itemMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.currentIndex = index
                            root.popupOpen = false
                            root.activated(index)
                        }
                    }

                    Keys.onReturnPressed: {
                        root.currentIndex = index
                        root.popupOpen = false
                        root.activated(index)
                    }

                    Keys.onEnterPressed: {
                        root.currentIndex = index
                        root.popupOpen = false
                        root.activated(index)
                    }
                }
            }
        }

        implicitHeight: Math.min(root.model.length * MichiTheme.rowHeightCompact + MichiTheme.spacing.xxs * 2, 300)
    }

    Keys.onUpPressed: function(event) {
        if (root.popupOpen) {
            var prev = Math.max(0, root.currentIndex - 1)
            root.currentIndex = prev
            event.accepted = true
        }
    }

    Keys.onDownPressed: function(event) {
        if (root.popupOpen) {
            var next = Math.min(root.model.length - 1, root.currentIndex + 1)
            root.currentIndex = next
            event.accepted = true
        } else {
            root.popupOpen = true
            event.accepted = true
        }
    }

    Keys.onReturnPressed: function(event) {
        if (root.popupOpen) {
            root.activated(root.currentIndex)
            root.popupOpen = false
            event.accepted = true
        }
    }

    Keys.onEnterPressed: function(event) {
        if (root.popupOpen) {
            root.activated(root.currentIndex)
            root.popupOpen = false
            event.accepted = true
        }
    }

    Keys.onEscapePressed: function(event) {
        if (root.popupOpen) {
            root.popupOpen = false
            event.accepted = true
        }
    }

    onActiveFocusChanged: {
        if (!root.activeFocus)
            root.popupOpen = false
    }
}
