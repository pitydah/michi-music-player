import QtQuick
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property bool checked: false
    property bool loading: false
    property string text: ""
    property string accessibleName: root.text !== "" ? root.text : "Interruptor"
    property string accessibleDescription: ""

    signal toggled(bool checked)

    implicitWidth: trackWidth + (root.text !== "" ? MichiTheme.spacing.sm + labelText.implicitWidth : 0)
    implicitHeight: Math.max(MichiTheme.minimumInteractiveSize, trackHeight + MichiTheme.spacing.xs * 2)

    Accessible.role: Accessible.CheckBox
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription
    Accessible.checked: root.checked

    readonly property int trackWidth: 44
    readonly property int trackHeight: 24
    readonly property int thumbSize: 20

    activeFocusOnTab: enabled && visible

    function toggle() {
        if (!root.enabled || root.loading) return
        root.checked = !root.checked
        root.toggled(root.checked)
    }

    MouseArea {
        anchors.fill: parent
        enabled: !root.loading
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggle()
    }

    Item {
        id: trackArea
        width: root.trackWidth
        height: root.trackHeight
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left

        Rectangle {
            anchors.fill: parent
            radius: parent.height / 2
            color: root.checked ? MichiTheme.colors.accentBlue : MichiTheme.colors.controlTrack
            border.width: root.activeFocus ? MichiTheme.focusWidth : 0
            border.color: root.activeFocus ? MichiTheme.colors.borderFocus : "transparent"

            Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
        }

        Rectangle {
            x: root.checked ? parent.width - root.thumbSize - 2 : 2
            y: (parent.height - root.thumbSize) / 2
            width: root.thumbSize
            height: root.thumbSize
            radius: root.thumbSize / 2
            color: root.enabled ? MichiTheme.colors.controlThumb : MichiTheme.colors.textMuted

            Behavior on x { NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic } }
        }
    }

    Text {
        id: labelText
        anchors.left: trackArea.right
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
