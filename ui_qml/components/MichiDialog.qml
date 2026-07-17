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

    function _wireKeyNavigation() {
        var first = focusScope.firstFocusable
        var last = focusScope.lastFocusable
        if (first && last && first !== last) {
            first.KeyNavigation.backtab = last
            last.KeyNavigation.tab = first
        }
    }

    function _isFocusable(item) {
        return item !== null && item !== undefined
            && item.visible !== false
            && item.enabled !== false
            && (item.activeFocusOnTab === true || (item.focusPolicy !== undefined && item.focusPolicy !== Qt.NoFocus))
    }

    function _findFirstFocusable(container) {
        if (!container || !container.data) return container
        for (var i = 0; i < container.data.length; i++) {
            var child = container.data[i]
            if (_isFocusable(child)) return child
            var sub = _findFirstFocusable(child)
            if (sub) return sub
        }
        return container.data.length > 0 ? container.data[0] : container
    }

    onOpened: {
        _savedFocus = root.parent ? root.parent.Window.activeFocusItem : null
        _wireKeyNavigation()
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

            readonly property Item firstFocusable: _findFirstFocusable(contentArea)
            readonly property Item lastFocusable: _findLastFocusable()

            function focusFirst() {
                firstFocusable.forceActiveFocus(Qt.TabFocusReason)
            }

            function focusLast() {
                lastFocusable.forceActiveFocus(Qt.BacktabFocusReason)
            }

            function _findLastFocusable() {
                for (var i = buttonsArea.data.length - 1; i >= 0; i--) {
                    var child = buttonsArea.data[i]
                    if (child !== undefined && child !== null)
                        return child
                }
                return buttonsArea
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
        running: root.opened && !root.reducedMotion
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
