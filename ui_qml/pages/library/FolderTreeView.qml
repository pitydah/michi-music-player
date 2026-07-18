import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Folder Tree View"
    objectName: "folderTreeView"
    focus: true
    id: root

    property var folderModel: null
    property string currentPath: ""

    signal folderSelected(string path)

    TreeView {
        focusPolicy: Qt.StrongFocus
        id: treeView
        anchors.fill: parent
        model: root.folderModel
        clip: true

        delegate: Item {
            id: delegate
            implicitHeight: 32
            implicitWidth: parent.width

            Rectangle {
                anchors.fill: parent
                color: model.folderPath === root.currentPath ? MichiTheme.colors.accentSurface :
                       mouse.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.xs
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: model.isExpandable ? (model.expanded ? "▼" : qsTr("▶")) : " "
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.badgeSize
                        width: 16
                        Accessible.role: Accessible.Icon
                        Accessible.name: model.isExpandable ? (model.expanded ? "Expandido" : "Colapsado") : ""
                    }

                    Rectangle {
                        width: 20; height: 20; radius: MichiTheme.radius.sm
                        color: MichiTheme.colors.borderInner
                        Text {
                            anchors.centerIn: parent
                            text: qsTr("FD")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.badgeSize
                            font.weight: MichiTheme.typography.weightBold
                        }
                    }

                    Column {
                        Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                        Text {
                            text: model.folderName || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight; width: parent.width
                        }
                        Text {
                            text: model.trackCount > 0 ? model.trackCount + " canciones" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            visible: text !== ""
                        }
                    }
                }

                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (model.isExpandable && !model.expanded) {
                            root.folderModel._items = []
                            root.folderModel.refresh("parent_path", model.folderPath)
                        }
                        root.folderSelected(model.folderPath || "")
                    }
                }
            }
        }
    }

    function navigateTo(path) {
        if (root.folderModel) {
            root.folderModel.refresh("parent_path", path)
        }
    }
}
