import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"

Item {
    id: root

    property string titleText: ""
    property string iconText: ""
    property bool open: false
    property int closePolicy: CloseOnEscape

    property Item contentItem: null
    property Item buttonsItem: null

    signal accepted()
    signal rejected()

    objectName: "BaseDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: titleText
    Accessible.description: "Diálogo"

    readonly property int CloseOnEscape: 1
    readonly property int CloseOnClickOutside: 2
    readonly property int CloseOnEscapeOrClickOutside: 3

    visible: open
    enabled: visible

    Keys.onEscapePressed: {
        if (root.closePolicy & root.CloseOnEscape) {
            root.open = false
            root.rejected()
        }
    }
    Keys.onReturnPressed: {
        if (root.buttonsItem && root.buttonsItem.confirmEnabled !== false)
            root.doAccept()
    }
    Keys.onEnterPressed: {
        if (root.buttonsItem && root.buttonsItem.confirmEnabled !== false)
            root.doAccept()
    }

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
            root._focusFirstInteractive()
        } else {
            root._restoreFocus()
        }
    }

    property Item _savedFocus: null
    property bool _opening: false

    function _focusFirstInteractive() {
        root._savedFocus = root.activeFocusItem || null
        var item = (root.contentItem && root.contentItem.focus) ? root.contentItem :
                   (root.buttonsItem && root.buttonsItem.focus) ? root.buttonsItem : null
        if (item) item.forceActiveFocus()
    }

    function _restoreFocus() {
        if (root._savedFocus) {
            root._savedFocus.forceActiveFocus()
            root._savedFocus = null
        }
    }

    NumberAnimation on opacity {
        from: 0; to: 1; duration: MichiTheme.motion.normal
        easing.type: Easing.OutCubic
        running: root.open
    }

    Behavior on scale {
        NumberAnimation { duration: MichiTheme.motion.fast; easing.type: Easing.OutBack }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceOverlay
        z: 9990
        opacity: root.open ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (root.closePolicy & root.CloseOnClickOutside) {
                    root.open = false
                    root.rejected()
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
            radius: MichiTheme.radiusMd
            color: MichiTheme.colors.surfaceCardElevated
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard

            ColumnLayout {
                id: contentLayout
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.md

                RowLayout {
                    id: headerRow
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.sm

                    Text {
                        id: iconDisplay
                        text: root.iconText
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        visible: root.iconText !== ""
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.titleText
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
                        Accessible.name: root.titleText
                    }
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

        QQC2.FocusTrap {
            active: root.visible
            focusItem: {
                var candidate = (root.contentItem && root.contentItem.focus) ? root.contentItem :
                               (root.buttonsItem && root.buttonsItem.focus) ? root.buttonsItem : null
                return candidate || root
            }
        }
    }
}
