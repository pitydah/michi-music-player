import QtQuick
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: root.controlObjectName

    property bool checked: false
    property bool tristate: false
    property bool partiallyChecked: false
    property bool loading: false
    property string text: ""
    property string accessibleName: root.text !== "" ? root.text : "Casilla"
    property string accessibleDescription: ""

    signal toggled(bool checked)

    implicitWidth: boxSize + (root.text !== "" ? MichiTheme.spacing.sm + labelText.implicitWidth : 0)
    implicitHeight: Math.max(MichiTheme.minimumInteractiveSize, boxSize + MichiTheme.spacing.xs * 2)

    Accessible.role: Accessible.CheckBox
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription
    Accessible.checked: root.checked

    readonly property int boxSize: 20

    activeFocusOnTab: enabled && visible

    function toggle() {
        if (!root.enabled || root.loading) return
        if (root.tristate) {
            if (!root.checked && !root.partiallyChecked) {
                root.checked = true
                root.partiallyChecked = false
            } else if (root.checked && !root.partiallyChecked) {
                root.checked = false
                root.partiallyChecked = true
            } else {
                root.checked = false
                root.partiallyChecked = false
            }
        } else {
            root.checked = !root.checked
        }
        root.toggled(root.checked)
    }

    MouseArea {
        anchors.fill: parent
        enabled: !root.loading
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggle()
    }

    Rectangle {
        id: box
        width: root.boxSize
        height: root.boxSize
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        radius: MichiTheme.radius.xs
        color: root.checked ? MichiTheme.colors.accentBlue : MichiTheme.colors.controlTrack
        border.width: root.activeFocus ? MichiTheme.focusWidth : (root.checked ? 0 : MichiTheme.borderWidth)
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

        Text {
            anchors.centerIn: parent
            text: root.partiallyChecked ? "\u2014" : "\u2713"
            color: root.checked || root.partiallyChecked ? MichiTheme.colors.textOnAccent : "transparent"
            font.pixelSize: 14
            font.weight: Font.Bold
        }
    }

    Text {
        id: labelText
        anchors.left: box.right
        anchors.leftMargin: MichiTheme.spacing.sm
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        color: root.enabled ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.bodySize
        visible: root.text !== ""
    }

    Keys.onSpacePressed: function(event) {
        root.toggle()
        event.accepted = true
    }

    Keys.onReturnPressed: function(event) {
        root.toggle()
        event.accepted = true
    }

    Keys.onEnterPressed: function(event) {
        root.toggle()
        event.accepted = true
    }
}
