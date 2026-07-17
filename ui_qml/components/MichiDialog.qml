import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

QQC2.Popup {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string titleText: ""
    property bool loading: false
    property string accessibleName: root.titleText
    property string accessibleDescription: ""

    property bool reducedMotion: false

    signal accepted()
    signal rejected()

    modal: true
    closePolicy: QQC2.Popup.CloseOnEscape

    Accessible.role: Accessible.Dialog
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    default property alias content: contentArea.data
    property alias buttons: buttonsArea.data

    width: Math.min(420, parent ? parent.width * 0.9 : 420)
    height: Math.min(contentColumn.implicitHeight + MichiTheme.spacing.xl * 2, parent ? parent.height * 0.8 : 600)
    anchors.centerIn: parent

    property Item _savedFocus: null

    onOpened: {
        _savedFocus = root.parent ? root.parent.Window.activeFocusItem : null
        root.forceActiveFocus()
        focusScope.focusFirst()
    }

    onClosed: {
        if (_savedFocus)
            _savedFocus.forceActiveFocus()
    }

    enter: Transition {
        enabled: !root.reducedMotion
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic }
        NumberAnimation { target: contentScale; property: "scale"; from: 0.92; to: 1.0; duration: MichiTheme.motion.normal; easing.type: Easing.OutCubic }
    }

    exit: Transition {
        enabled: !root.reducedMotion
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: MichiTheme.motion.fast; easing.type: Easing.InCubic }
        NumberAnimation { target: contentScale; property: "scale"; from: 1.0; to: 0.92; duration: MichiTheme.motion.fast; easing.type: Easing.InCubic }
    }

    background: Rectangle {
        id: dialogBg
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceCardElevated
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
    }

    contentItem: Item {
        implicitWidth: 400
        implicitHeight: contentColumn.implicitHeight

        FocusScope {
            id: focusScope
            anchors.fill: parent

            property Item firstFocusable: contentArea.children.length > 0 ? contentArea.children[0] : buttonsArea
            property Item lastFocusable: buttonsArea

            function focusFirst() {
                firstFocusable.forceActiveFocus(Qt.TabFocusReason)
            }

            function focusLast() {
                lastFocusable.forceActiveFocus(Qt.BacktabFocusReason)
            }

            Item {
                id: contentScale
                anchors.fill: parent

                ColumnLayout {
                id: contentColumn
                anchors.fill: parent
                spacing: MichiTheme.spacing.md

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: MichiTheme.spacing.md
                    Layout.leftMargin: MichiTheme.spacing.xl
                    Layout.rightMargin: MichiTheme.spacing.xl
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
                    Layout.leftMargin: MichiTheme.spacing.xl
                    Layout.rightMargin: MichiTheme.spacing.xl
                    clip: true
                }

                Item {
                    id: buttonsArea
                    Layout.fillWidth: true
                    Layout.bottomMargin: MichiTheme.spacing.md
                    Layout.leftMargin: MichiTheme.spacing.xl
                    Layout.rightMargin: MichiTheme.spacing.xl
                    implicitHeight: 40
                }
            }
        }
        }
    }

    NumberAnimation on opacity {
        from: 0; to: 1; duration: MichiTheme.motion.normal
        easing.type: Easing.OutCubic
        running: root.opened
    }

    Keys.onReturnPressed: {
        if (!root.loading)
            root.accepted()
    }

    Keys.onEnterPressed: {
        if (!root.loading)
            root.accepted()
    }
}
