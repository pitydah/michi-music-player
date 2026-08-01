import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../materials"

Item {
    id: root
    objectName: "baseDialog"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: titleText !== "" ? titleText : defaultTitle
    Accessible.description: qsTr("Diálogo")

    property string titleText: ""
    property string defaultTitle: qsTr("Diálogo")
    property string iconText: ""
    property bool open: false
    property int closePolicy: BaseDialog.CloseOnEscape

    property Item contentItem: null
    property Item buttonsItem: null

    // Ordered tab chain used by the FocusTrap while the dialog is open.
    // Subclasses set this to their interactive controls in tab order.
    property list<Item> focusTrapItems: []

    signal accepted()
    signal rejected()

    // Close policy constants (QQC2 Dialog-style). Inherited by subclasses
    // through the component type scope; lowercase aliases kept for compat.
    enum ClosePolicy {
        CloseOnEscape = 1,
        CloseOnClickOutside = 2,
        CloseOnEscapeOrClickOutside = 3
    }
    readonly property int closeOnEscape: BaseDialog.CloseOnEscape
    readonly property int closeOnClickOutside: BaseDialog.CloseOnClickOutside
    readonly property int closeOnEscapeOrClickOutside: BaseDialog.CloseOnEscapeOrClickOutside

    // Window overlay: the dialog covers its parent and stacks above content.
    anchors.fill: parent
    z: 9990
    visible: open
    enabled: visible

    Keys.onEscapePressed: {
        if (root.closePolicy & BaseDialog.CloseOnEscape)
            root.doReject()
    }
    Keys.onReturnPressed: root._acceptIfEnabled()
    Keys.onEnterPressed: root._acceptIfEnabled()
    Keys.onTabPressed: focusTrap.cycleForward()
    Keys.onBacktabPressed: focusTrap.cycleBackward()

    function _confirmEnabled() {
        if (!root.buttonsItem)
            return true
        if (root.buttonsItem.confirmEnabled === undefined)
            return true
        return root.buttonsItem.confirmEnabled !== false
    }

    function _acceptIfEnabled() {
        if (root._confirmEnabled())
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
            root._saveFocus()
            root.forceActiveFocus()
            root._focusFirstInteractive()
        } else {
            root._restoreFocus()
        }
    }

    property Item _savedFocus: null

    function _windowFocusItem() {
        var win = root.Window.window
        return win ? win.activeFocusItem : null
    }

    function _saveFocus() {
        root._savedFocus = root._windowFocusItem()
    }

    function _focusFirstInteractive() {
        var item = (root.contentItem && root.contentItem.focus) ? root.contentItem :
                   (root.buttonsItem && root.buttonsItem.focus) ? root.buttonsItem : null
        if (item)
            item.forceActiveFocus()
        else
            focusTrap.focusFirst()
    }

    function _restoreFocus() {
        var target = root._savedFocus
        root._savedFocus = null
        if (target && target.Window.window)
            target.forceActiveFocus()
    }

    // Reparent assigned content/buttons into the dialog frame so they are
    // actually rendered (an Item assigned to a property has no visual parent).
    onContentItemChanged: {
        if (root.contentItem)
            root.contentItem.parent = contentArea
    }
    onButtonsItemChanged: {
        if (root.buttonsItem)
            root.buttonsItem.parent = buttonsArea
    }

    FocusTrap {
        id: focusTrap
        container: dialogFrame
        items: root.focusTrapItems
        active: root.open
    }

    NumberAnimation on opacity {
        from: 0; to: 1; duration: MichiTheme.motion.normal
        easing.type: Easing.OutCubic
        running: root.open
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
                if (root.closePolicy & BaseDialog.CloseOnClickOutside)
                    root.doReject()
            }
        }
    }

    FocusScope {
        id: dialogFrame
        anchors.centerIn: parent
        width: Math.min(420, parent.width * 0.9)
        height: Math.min(contentLayout.implicitHeight + MichiTheme.spacing.xl * 2, parent.height * 0.8)
        z: 9991
        scale: root.open ? 1 : 0.92

        Behavior on scale {
            NumberAnimation { duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic }
        }

        PopupMaterial {
            anchors.fill: parent
            radius: MichiTheme.radius.md

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
                        Accessible.role: Accessible.Graphic
                        Accessible.name: root.Accessible.name + qsTr(" icono")
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.titleText !== "" ? root.titleText : root.defaultTitle
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
                    }
                }

                Item {
                    id: contentArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    implicitHeight: root.contentItem ? root.contentItem.implicitHeight || 40 : 0
                    clip: true
                }

                Item {
                    id: buttonsArea
                    Layout.fillWidth: true
                    implicitHeight: root.buttonsItem ? root.buttonsItem.implicitHeight || 40 : 0
                }
            }
        }
    }
}
