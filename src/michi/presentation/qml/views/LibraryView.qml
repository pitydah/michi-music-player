import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

MichiPanel {
    id: root

    property string currentTab: "songs"

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space8

        LibraryHeader {}

        LibraryToolbar {}

        LibraryTabs {
            currentTab: root.currentTab
            onCurrentTabChanged: root.currentTab = currentTab
        }

        LibraryContentHost {
            currentTab: root.currentTab
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
