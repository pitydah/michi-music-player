import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root

    property string currentTab: "songs"
    signal tabRequested(string tab)
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

    objectName: "libraryNavigationRail"
    implicitHeight: MichiMetrics.controlMedium
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.md
        color: MichiSemanticColors.controlSurface
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
    }

    function ensureCurrentTabVisible() {
        for (var index = 0; index < tabRepeater.count; index++) {
            var item = tabRepeater.itemAt(index)
            if (!item || root.tabs[index].value !== root.currentTab)
                continue
            var leftEdge = item.x
            var rightEdge = item.x + item.width
            if (leftEdge < navigationFlickable.contentX)
                navigationFlickable.contentX = leftEdge
            else if (rightEdge > navigationFlickable.contentX + root.width)
                navigationFlickable.contentX = Math.min(
                    navigationFlickable.contentWidth - root.width,
                    rightEdge - root.width)
            return
        }
    }

    onCurrentTabChanged: Qt.callLater(root.ensureCurrentTabVisible)
    onWidthChanged: Qt.callLater(root.ensureCurrentTabVisible)

    Flickable {
        id: navigationFlickable
        anchors.fill: parent
        anchors.margins: 2
        contentWidth: tabRow.implicitWidth
        contentHeight: height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick

        RowLayout {
            id: tabRow
            height: parent.height
            spacing: 1

            Repeater {
                id: tabRepeater
                model: root.tabs
                delegate: TabButton {
                    id: tabButton
                    required property var modelData
                    Layout.preferredHeight: tabRow.height
                    Layout.preferredWidth: tabContent.implicitWidth + MichiSpacing.sm * 2
                    text: modelData.label
                    checked: root.currentTab === modelData.value
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    Accessible.role: Accessible.PageTab
                    Accessible.name: text

                    contentItem: RowLayout {
                        id: tabContent
                        spacing: MichiSpacing.xs
                        Rectangle {
                            Layout.preferredWidth: 24
                            Layout.preferredHeight: 24
                            radius: 8
                            color: tabButton.checked
                                ? MichiSemanticColors.auroraCyanSurface
                                : tabButton.hovered
                                    ? MichiSemanticColors.surfaceHover : "transparent"
                            border.width: tabButton.checked ? 1 : 0
                            border.color: MichiSemanticColors.auroraCyanBorderStrong

                            MichiIcon {
                                anchors.centerIn: parent
                                width: 14
                                height: 14
                                name: tabButton.modelData.icon
                                iconColor: tabButton.checked
                                    ? MichiPalette.auroraCyan
                                    : tabButton.hovered
                                        ? MichiPalette.textPrimary
                                        : MichiPalette.textSecondary
                                strokeWidth: tabButton.checked ? 1.9 : 1.6
                            }
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
                        radius: MichiRadius.sm
                        color: tabButton.pressed
                            ? MichiSemanticColors.surfacePressed
                            : tabButton.checked
                                ? MichiSemanticColors.surfaceSelected
                                : tabButton.hovered
                                    ? MichiSemanticColors.surfaceHover : "transparent"
                        border.width: tabButton.checked || tabButton.hovered ? 1 : 0
                        border.color: tabButton.checked
                            ? MichiSemanticColors.auroraCyanBorderSubtle
                            : MichiSemanticColors.borderSubtle
                        scale: tabButton.pressed ? 0.98 : 1

                        Rectangle {
                            visible: tabButton.checked
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: MichiSpacing.sm
                            anchors.rightMargin: MichiSpacing.sm
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
                    onClicked: root.tabRequested(modelData.value)
                }
            }
        }
    }
}
