import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root

    property string currentTab: "songs"
    readonly property var tabs: [
        { value: "songs", label: "Songs", icon: "track" },
        { value: "albums", label: "Albums", icon: "album" },
        { value: "artists", label: "Artists", icon: "artist" },
        { value: "genres", label: "Genres", icon: "genre" },
        { value: "folders", label: "Folders", icon: "folder" },
        { value: "favorites", label: "Favorites", icon: "heart" },
        { value: "history", label: "History", icon: "history" },
        { value: "recently", label: "Recently Added", icon: "recent" },
        { value: "playlists", label: "Playlists", icon: "playlist" }
    ]

    implicitHeight: 44

    MichiGlassSurface {
        id: navigationRail
        objectName: "libraryNavigationRail"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(root.width, tabRow.implicitWidth + MichiSpacing.sm * 2)
        contentPadding: MichiSpacing.xs
        elevation: "subtle"
        shadowed: true
        textured: true

        Flickable {
            anchors.fill: parent
            contentWidth: tabRow.implicitWidth
            contentHeight: height
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            RowLayout {
                id: tabRow
                height: parent.height
                spacing: MichiSpacing.xs

                Repeater {
                    model: root.tabs
                    delegate: TabButton {
                        id: tabButton
                        required property var modelData
                        Layout.preferredHeight: tabRow.height
                        Layout.preferredWidth: tabContent.implicitWidth + MichiSpacing.lg
                        text: modelData.label
                        checked: root.currentTab === modelData.value
                        focusPolicy: Qt.StrongFocus
                        hoverEnabled: true
                        Accessible.role: Accessible.PageTab
                        Accessible.name: text

                        contentItem: RowLayout {
                            id: tabContent
                            spacing: MichiSpacing.sm
                            MichiIcon {
                                Layout.preferredWidth: MichiMetrics.iconSmall
                                Layout.preferredHeight: MichiMetrics.iconSmall
                                name: tabButton.modelData.icon
                                iconColor: tabButton.checked
                                    ? MichiPalette.auroraCyan
                                    : tabButton.hovered
                                        ? MichiPalette.textPrimary : MichiPalette.textSecondary
                            }
                            MichiText {
                                text: tabButton.text
                                role: "secondary"
                                color: tabButton.checked
                                    ? MichiPalette.textPrimary : MichiPalette.textSecondary
                                font.weight: tabButton.checked ? Font.DemiBold : Font.Normal
                            }
                        }

                        background: Rectangle {
                            radius: MichiRadius.md
                            color: tabButton.pressed
                                ? MichiSemanticColors.surfacePressed
                                : tabButton.checked
                                    ? MichiSemanticColors.surfaceSelected
                                    : tabButton.hovered
                                        ? MichiSemanticColors.surfaceHover : "transparent"
                            border.width: tabButton.checked ? 1 : 0
                            border.color: MichiSemanticColors.auroraCyanBorderSubtle
                            scale: tabButton.pressed ? 0.98 : 1

                            Rectangle {
                                visible: tabButton.checked
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: MichiSpacing.md
                                anchors.rightMargin: MichiSpacing.md
                                height: 2
                                radius: 1
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: MichiPalette.auroraBlue }
                                    GradientStop { position: 1; color: MichiPalette.auroraCyan }
                                }
                            }
                            Behavior on color {
                                enabled: !MichiAccessibility.reducedMotion
                                ColorAnimation { duration: MichiMotion.micro }
                            }
                            Behavior on scale {
                                enabled: !MichiAccessibility.reducedMotion
                                NumberAnimation {
                                    duration: MichiMotion.micro
                                    easing.type: MichiMotion.outCubic
                                }
                            }
                            MichiFocusRing { visualFocus: tabButton.visualFocus }
                        }
                        onClicked: root.currentTab = modelData.value
                    }
                }
            }
        }
    }
}
