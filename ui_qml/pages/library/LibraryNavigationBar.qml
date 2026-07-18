import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Navigation Bar"
    objectName: "libraryNavigationBar"
    focus: true
    id: root
    width: parent.width; height: MichiTheme.toolbarHeight

    MichiResponsive { id: responsive; availableWidth: root.width }

    property int currentTab: 0
    property string searchText: ""

    signal searchTextUpdated(string text)

    function clearSearch() { searchInput.text = "" }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceCard

        TabBar {
            Accessible.role: Accessible.PageTabList
            id: tabBar
            activeFocusOnTab: true

            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiTheme.spacing.md
            height: parent.height
            background: Rectangle { color: "transparent" }



            Repeater {
                model: ["Canciones", "Álbumes", "Artistas", "Carpetas"]
                TabButton {
                    objectName: "libraryNavTab" + index
                    text: modelData
                    font.pixelSize: MichiTheme.typography.bodySize
                    contentItem: Text {
                        text: parent.text
                        color: tabBar.currentIndex === index ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                        font: parent.font
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: "transparent"
                        Rectangle {
                            anchors.bottom: parent.bottom;         width: parent.width; height: MichiTheme.borderWidth; radius: MichiTheme.radius.xs
                            color: MichiTheme.colors.accentBlue
                            visible: tabBar.currentIndex === index
                        }
                    }
                    onClicked: { root.currentTab = index; tabBar.currentIndex = index }
                }
            }
        }

        MichiSearchField {
            id: searchInput
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: MichiTheme.spacing.md
            width: responsive.compact ? 140 : 200; height: 28
            placeholderText: qsTr("Buscar en biblioteca...")
            onSearchTextChanged: {
                root.searchText = text
                root.searchTextUpdated(text)
            }
        }
    }
}
