import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    width: parent.width; height: 38

    property int currentTab: 0
    property string searchText: ""

    signal searchTextChanged(string text)

    function clearSearch() { searchInput.text = "" }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surface

        TabBar {
            id: tabBar
            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiTheme.spacing.md
            height: parent.height
            background: Rectangle { color: "transparent" }

            Repeater {
                model: ["Canciones", "Álbumes", "Artistas", "Carpetas"]
                TabButton {
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
                            anchors.bottom: parent.bottom; width: parent.width; height: 2; radius: 1
                            color: MichiTheme.colors.accentBlue
                            visible: tabBar.currentIndex === index
                        }
                    }
                    onClicked: { root.currentTab = index; tabBar.currentIndex = index }
                }
            }
        }

        SearchField {
            id: searchInput
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: MichiTheme.spacing.md
            width: 200; height: 28
            placeholderText: "Buscar en biblioteca..."
            onSearchTextChanged: {
                root.searchText = text
                root.searchTextChanged(text)
            }
        }
    }
}
