import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    id: root
    objectName: "folderBreadcrumb"
    focus: true

    property string path: ""
    readonly property var entries: root.buildEntries(root.path)

    signal navigate(int index)
    signal navigateTo(string path)

    Accessible.role: Accessible.ToolBar
    Accessible.name: qsTr("Ruta de carpetas")
    Accessible.description: root.path || qsTr("Raíz de la biblioteca")

    implicitHeight: 38

    function normalizedPath(value) {
        var normalized = (value || "").replace(/\\/g, "/")
        while (normalized.length > 1 && normalized.endsWith("/"))
            normalized = normalized.slice(0, -1)
        return normalized
    }

    function buildEntries(value) {
        var normalized = root.normalizedPath(value)
        var result = [{ label: qsTr("Biblioteca"), path: "" }]
        if (!normalized)
            return result

        var absolute = normalized.startsWith("/")
        var parts = normalized.split("/").filter(function(part) { return part !== "" })
        var current = absolute ? "/" : ""

        for (var index = 0; index < parts.length; index++) {
            var part = parts[index]
            if (current === "/")
                current += part
            else if (current === "")
                current = part
            else
                current += "/" + part
            result.push({ label: part, path: current })
        }
        return result
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle

        Flickable {
            id: breadcrumbFlick
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.sm
            anchors.rightMargin: MichiTheme.spacing.sm
            contentWidth: breadcrumbRow.width
            contentHeight: height
            clip: true
            flickableDirection: Flickable.HorizontalFlick
            boundsBehavior: Flickable.StopAtBounds

            onContentWidthChanged: contentX = Math.max(0, contentWidth - width)

            Row {
                id: breadcrumbRow
                width: implicitWidth
                height: parent.height
                spacing: MichiTheme.spacing.xs

                Repeater {
                    model: root.entries

                    Row {
                        required property int index
                        required property var modelData
                        height: parent.height
                        spacing: MichiTheme.spacing.xs

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: index > 0
                            text: "›"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: crumbText.implicitWidth + MichiTheme.spacing.md
                            height: 28
                            radius: MichiTheme.radius.pill
                            color: crumbMouse.containsMouse
                                   ? MichiTheme.colors.surfaceHover
                                   : index === root.entries.length - 1
                                     ? MichiTheme.colors.accentSelection
                                     : "transparent"

                            Accessible.role: Accessible.Button
                            Accessible.name: modelData.label
                            Accessible.description: modelData.path || qsTr("Raíz de la biblioteca")
                            Accessible.onPressAction: {
                                root.navigate(index - 1)
                                root.navigateTo(modelData.path)
                            }

                            Text {
                                id: crumbText
                                anchors.centerIn: parent
                                text: modelData.label
                                color: index === root.entries.length - 1
                                       ? MichiTheme.colors.accentBlue
                                       : MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                font.weight: index === root.entries.length - 1
                                             ? MichiTheme.typography.weightSemiBold
                                             : MichiTheme.typography.weightMedium
                            }

                            MouseArea {
                                id: crumbMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.navigate(index - 1)
                                    root.navigateTo(modelData.path)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
