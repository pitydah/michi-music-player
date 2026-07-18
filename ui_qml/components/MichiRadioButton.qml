import QtQuick
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property bool checked: false
    property bool loading: false
    property string text: ""
    property string group: ""
    property string accessibleName: root.text !== "" ? root.text : qsTr("Opci\u00F3n")
    property string accessibleDescription: ""

    signal toggled(bool checked)

    implicitWidth: circleSize + (root.text !== "" ? MichiTheme.spacing.sm + labelText.implicitWidth : 0)
    implicitHeight: Math.max(MichiTheme.minimumInteractiveSize, circleSize + MichiTheme.spacing.xs * 2)

    Accessible.role: Accessible.RadioButton
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription
    Accessible.checked: root.checked

    readonly property int circleSize: 20

    activeFocusOnTab: enabled && visible

    function toggle() {
        if (!root.enabled || root.loading || root.checked) return
        root.checked = true
        root.toggled(true)
    }

    MouseArea {
        anchors.fill: parent
        enabled: !root.loading
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggle()
    }

    Rectangle {
        id: circle
        width: root.circleSize
        height: root.circleSize
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        radius: root.circleSize / 2
        color: "transparent"
        border.width: root.activeFocus ? MichiTheme.focusWidth : 2
        border.color: root.checked ? MichiTheme.colors.accentBlue
                     : root.activeFocus ? MichiTheme.colors.borderFocus
                     : MichiTheme.colors.borderCard

        Rectangle {
            anchors.centerIn: parent
            width: root.circleSize - 6
            height: root.circleSize - 6
            radius: (root.circleSize - 6) / 2
            color: root.checked ? MichiTheme.colors.accentBlue : "transparent"

            Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
        }
    }

    Text {
        id: labelText
        anchors.left: circle.right
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
