import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string titleText: ""
    property bool open: false
    property int closePolicy: QQC2.Popup.CloseOnEscape
    property bool loading: false
    property string accessibleName: root.titleText
    property string accessibleDescription: ""

    property Item contentItem: null
    property Item buttonsItem: null

    signal accepted()
    signal rejected()

    visible: root.open
    enabled: visible

    Accessible.role: Accessible.Dialog
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    function doAccept() {
        root.open = false
        root.accepted()
    }

    function doReject() {
        root.open = false
        root.rejected()
    }

    onOpenChanged: {
        if (root.open) {
            root.forceActiveFocus()
        }
    }

    Keys.onEscapePressed: {
        if (root.closePolicy & QQC2.Popup.CloseOnEscape) {
            root.doReject()
        }
    }

    Keys.onReturnPressed: {
        if (!root.loading)
            root.doAccept()
    }

    Keys.onEnterPressed: {
        if (!root.loading)
            root.doAccept()
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990
        opacity: root.open ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (root.closePolicy & QQC2.Popup.CloseOnPressOutside) {
                    root.doReject()
                }
            }
        }
    }

    FocusScope {
        id: dialogFrame
        anchors.centerIn: parent
        width: Math.min(420, parent.width * 0.9)
        height: Math.min(contentLayout.implicitHeight + MichiTheme.spacing.xl * 2, parent.height * 0.8)
        z: 9991
        focus: root.visible
        scale: root.open ? 1 : 0.92

        Behavior on scale {
            NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic }
        }

        Rectangle {
            anchors.fill: parent
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceCardElevated
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard

            ColumnLayout {
                id: contentLayout
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.md

                Text {
                    Layout.fillWidth: true
                    text: root.titleText
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    wrapMode: Text.WordWrap
                    visible: root.titleText !== ""
                }

                Item {
                    id: contentArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    implicitHeight: root.contentItem ? root.contentItem.implicitHeight || 40 : 0
                    clip: true

                    onChildrenChanged: {
                        if (contentArea.children.length > 0)
                            root.contentItem = contentArea.children[0]
                    }
                }

                Item {
                    id: buttonsArea
                    Layout.fillWidth: true
                    implicitHeight: root.buttonsItem ? root.buttonsItem.implicitHeight || 40 : 0

                    onChildrenChanged: {
                        if (buttonsArea.children.length > 0)
                            root.buttonsItem = buttonsArea.children[0]
                    }
                }
            }
        }
    }

    NumberAnimation on opacity {
        from: 0; to: 1; duration: MichiTheme.motion.normal
        easing.type: Easing.OutCubic
        running: root.open
    }
}
