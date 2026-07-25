import QtQuick
import QtQuick.Layouts
import "../../theme"

Rectangle {
    id: root
    objectName: "pageSurface"
    color: MichiTheme.colors.bgContent
    radius: width < MichiTheme.breakpoints.compact ? 0 : MichiTheme.radius.md
    border.width: width < MichiTheme.breakpoints.compact ? 0 : MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderSubtle
    clip: true

    property alias pageHeaderZone: headerHost.data
    property alias pageToolbarZone: toolbarHost.data
    default property alias pageContent: contentViewport.data

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            id: headerHost
            objectName: "pageHeaderZone"
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            visible: children.length > 0
        }

        Item {
            id: toolbarHost
            objectName: "pageToolbarZone"
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            visible: children.length > 0
        }

        Item {
            id: contentViewport
            objectName: "pageContentViewport"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
        }
    }
}
