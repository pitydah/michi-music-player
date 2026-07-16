import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

QQC2.Popup {
    id: root

    property string title: "Ordenar por"
    property var options: []
    property string currentOption: ""
    property bool ascending: true
    property int selectedIndex: -1

    signal sortChanged(string option, bool ascending)
    signal ascendingToggled()

    objectName: "SortMenu"

    Accessible.role: Accessible.PopupMenu
    Accessible.name: title

    width: Math.min(300, parent ? parent.width * 0.8 : 300)
    height: Math.min(implicitHeight, 400)
    padding: MichiTheme.spacing.xs
    closePolicy: QQC2.Popup.CloseOnEscape | QQC2.Popup.CloseOnPressOutside

    background: Rectangle {
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
    }

    contentItem: Column {
        spacing: MichiTheme.spacing.xs

        Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sort Menu"
    objectName: "sortMenu"
    focus: true
            width: parent.width
            height: MichiTheme.rowHeightComfortable

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: MichiTheme.spacing.sm
                text: root.title
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
                font.weight: MichiTheme.typography.weightMedium
            }

            QQC2.AbstractButton {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: MichiTheme.spacing.sm
                focusPolicy: Qt.StrongFocus

                Accessible.role: Accessible.Button
                Accessible.name: "Alternar orden " + (root.ascending ? "ascendente" : "descendente")

                contentItem: Text {
                    text: root.ascending ? "\u25B2 Asc" : "\u25BC Desc"
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: MichiTheme.typography.weightMedium
                }

                background: Item {}

                onClicked: {
                    root.ascending = !root.ascending
                    root.ascendingToggled()
                    root.sortChanged(root.currentOption, root.ascending)
                }
            }
        }

        Repeater {
            model: root.options

            delegate: QQC2.AbstractButton {
                id: optionDelegate
                width: parent.width
                height: MichiTheme.rowHeightComfortable
                focusPolicy: Qt.StrongFocus

                Accessible.role: Accessible.MenuItem
                Accessible.name: modelData
                Accessible.description: (modelData === root.currentOption ? "Seleccionado" : "") + " " + (root.ascending ? "ascendente" : "descendente")

                background: Rectangle {
                    radius: MichiTheme.radiusSm
                    color: modelData === root.currentOption
                           ? MichiTheme.colors.accentSelection
                           : optionDelegate.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                }

                contentItem: Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: MichiTheme.spacing.sm
                    text: {
                        var txt = modelData
                        if (modelData === root.currentOption) {
                            txt = root.ascending ? "\u25B2 " : "\u25BC "
                            return txt + modelData
                        }
                        return txt
                    }
                    color: modelData === root.currentOption
                           ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: modelData === root.currentOption
                                 ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                }

                onClicked: {
                    root.currentOption = modelData
                    root.sortChanged(modelData, root.ascending)
                    root.close()
                }

                Keys.onReturnPressed: clicked()
                Keys.onEnterPressed: clicked()
            }
        }
    }
}
