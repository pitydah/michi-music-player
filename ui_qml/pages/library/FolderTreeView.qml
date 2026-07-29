import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components"
import "../../theme"

Item {
    id: root
    objectName: "folderTreeView"
    focus: true

    property var folderModel: null
    property string currentPath: ""

    signal folderSelected(string path)

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Carpetas")
    Accessible.description: root.currentPath || qsTr("Raíz de la biblioteca")

    function navigateTo(path) {
        root.currentPath = path || ""
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        TreeView {
            id: folderTree
            objectName: "folderTree"
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xs
            model: root.folderModel
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true
            focus: true

            ScrollBar.vertical: ScrollBar {
                width: 8
                policy: ScrollBar.AsNeeded
            }

            delegate: Rectangle {
                id: folderRow
                required property int row
                required property int depth
                required property bool expanded
                required property bool hasChildren
                required property string path
                required property string name

                implicitWidth: folderTree.width
                implicitHeight: 46
                readonly property bool selected: folderRow.path === root.currentPath
                color: selected
                       ? MichiTheme.colors.accentSelection
                       : folderMouse.containsMouse
                         ? MichiTheme.colors.surfaceHover
                         : "transparent"
                radius: MichiTheme.radius.md
                border.width: selected ? MichiTheme.borderWidth : 0
                border.color: MichiTheme.colors.borderActive

                Accessible.role: Accessible.Button
                Accessible.name: folderRow.name || qsTr("Carpeta")
                Accessible.onPressAction: root.folderSelected(folderRow.path)

                MouseArea {
                    id: folderMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onDoubleClicked: {
                        if (folderRow.hasChildren)
                            folderTree.toggleExpanded(folderRow.row)
                    }
                    onClicked: root.folderSelected(folderRow.path)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.sm + folderRow.depth * MichiTheme.spacing.lg
                    anchors.rightMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    MichiIconButton {
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 28
                        visible: folderRow.hasChildren
                        iconSource: folderRow.expanded
                                    ? "../../../icons/actions/chevron-down.svg"
                                    : "../../../icons/actions/chevron-right.svg"
                        tooltipText: folderRow.expanded
                                     ? qsTr("Contraer carpeta")
                                     : qsTr("Expandir carpeta")
                        accessibleName: tooltipText
                        symbolic: true
                        onClicked: folderTree.toggleExpanded(folderRow.row)
                    }

                    Text {
                        Layout.fillWidth: true
                        text: folderRow.name || qsTr("Carpeta")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideMiddle
                    }
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: !root.folderModel
            text: qsTr("No hay carpetas configuradas")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
        }
    }
}
