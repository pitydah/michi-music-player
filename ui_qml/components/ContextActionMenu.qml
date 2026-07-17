import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

QQC2.Popup {
    id: root

    property var actions: []
    property int highlightedIndex: -1

    signal actionTriggered(int index, var action)

    objectName: "ContextActionMenu"

    Accessible.role: Accessible.PopupMenu
    Accessible.name: "Menú contextual"

    width: Math.min(280, parent ? parent.width * 0.8 : 280)
    height: Math.min(implicitHeight, 480)
    padding: MichiTheme.spacing.xs
    closePolicy: QQC2.Popup.CloseOnEscape | QQC2.Popup.CloseOnPressOutside

    background: Rectangle {
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
    }

    contentItem: ListView {
        id: listView
        width: parent.width
        height: contentHeight
        interactive: contentHeight > height
        spacing: 0
        currentIndex: root.highlightedIndex

        model: root.actions

        delegate: Item {
            width: listView.width
            height: modelData.separator === true || modelData.divider === true
                    ? separatorItem.height
                    : actionRow.implicitHeight + MichiTheme.spacing.sm * 2

            Rectangle {
    focus: true
                id: separatorItem
                width: parent.width
                height: modelData.separator === true || modelData.divider === true ? 1 : 0
                color: MichiTheme.colors.borderInner
                visible: modelData.separator === true || modelData.divider === true
            }

            Row {
                id: actionRow
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm
                visible: modelData.separator !== true && modelData.divider !== true

                Rectangle {
                    anchors.fill: parent
                    radius: MichiTheme.radius.sm
                    color: {
                        if (modelData.enabled === false) return "transparent"
                        var isHighlighted = ListView.isCurrentItem
                        return mouseArea.containsMouse || isHighlighted
                               ? MichiTheme.colors.surfaceHover : "transparent"
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.icon || ""
                    color: modelData.enabled === false
                           ? MichiTheme.colors.textMuted : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: modelData.icon !== undefined && modelData.icon !== ""
                    width: 20
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label || modelData.text || ""
                    color: {
                        if (modelData.danger) return MichiTheme.colors.error
                        if (modelData.enabled === false) return MichiTheme.colors.textMuted
                        return MichiTheme.colors.textPrimary
                    }
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: modelData.danger ? MichiTheme.typography.weightMedium
                                                   : MichiTheme.typography.weightNormal
                }

                Item {
                    Layout.fillWidth: true
                    height: 1
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.shortcut || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: modelData.shortcut !== undefined && modelData.shortcut !== ""
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.value || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: modelData.value !== undefined && modelData.value !== ""
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                enabled: modelData.enabled !== false && modelData.separator !== true && modelData.divider !== true

                Accessible.description: modelData.description || "Acción del menú contextual"

                onClicked: {
                    if (modelData.enabled !== false) {
                        root.actionTriggered(index, modelData)
                        root.close()
                    }
                }
            }

            Keys.onReturnPressed: {
                if (modelData.enabled !== false && modelData.separator !== true && modelData.divider !== true) {
                    root.actionTriggered(index, modelData)
                    root.close()
                }
            }
            Keys.onEnterPressed: {
                if (modelData.enabled !== false && modelData.separator !== true && modelData.divider !== true) {
                    root.actionTriggered(index, modelData)
                    root.close()
                }
            }
        }
    }
}
