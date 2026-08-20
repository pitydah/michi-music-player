import QtQuick
import QtQuick.Controls.Basic
import "../theme"

Flickable {
    id: root
    property string currentTab: "songs"
    readonly property var tabs: [
        { value: "songs", label: "Songs" },
        { value: "albums", label: "Albums" },
        { value: "artists", label: "Artists" },
        { value: "genres", label: "Genres" },
        { value: "folders", label: "Folders" },
        { value: "favorites", label: "Favorites" },
        { value: "history", label: "History" },
        { value: "recently", label: "Recently Added" },
        { value: "playlists", label: "Playlists" }
    ]
    implicitHeight: MichiMetrics.controlMedium
    contentWidth: tabRow.width
    contentHeight: height
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    Row {
        id: tabRow
        height: parent.height
        spacing: MichiSpacing.xs
        Repeater {
            model: root.tabs
            delegate: TabButton {
                id: tabButton
                required property var modelData
                height: tabRow.height
                text: modelData.label
                checked: root.currentTab === modelData.value
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.PageTab
                Accessible.name: text
                contentItem: Text {
                    text: tabButton.text
                    color: tabButton.checked ? MichiPalette.textPrimary : MichiPalette.textSecondary
                    font.family: MichiTypography.family
                    font.pixelSize: MichiTypography.secondary
                    font.weight: tabButton.checked ? Font.DemiBold : Font.Normal
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: MichiRadius.md
                    color: tabButton.checked ? MichiSemanticColors.surfaceSelected
                        : tabButton.hovered ? MichiSemanticColors.surfaceHover : "transparent"
                    border.width: tabButton.checked ? 1 : 0
                    border.color: Qt.rgba(0.298, 0.651, 1, 0.2)
                    Rectangle {
                        visible: tabButton.checked
                        height: 2
                        radius: 1
                        color: MichiPalette.auroraBlue
                        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                        anchors.leftMargin: MichiSpacing.sm; anchors.rightMargin: MichiSpacing.sm
                    }
                }
                onClicked: root.currentTab = modelData.value
            }
        }
    }
}
