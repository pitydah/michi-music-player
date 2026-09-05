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
        // LIB-A §41: labels traducidos (los valores internos no cambian).
        { value: "songs", label: qsTr("Songs"), icon: "track" },
        { value: "albums", label: qsTr("Albums"), icon: "album" },
        { value: "artists", label: qsTr("Artists"), icon: "artist" },
        { value: "genres", label: qsTr("Genres"), icon: "genre" },
        { value: "favorites", label: qsTr("Favorites"), icon: "heart" },
        { value: "history", label: qsTr("History"), icon: "history" },
        { value: "recently", label: qsTr("Recently Added"), icon: "recent" }
    ]

    objectName: "libraryNavigationRail"
    implicitHeight: MichiMetrics.controlLarge
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: MichiPalette.smoke
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
        anchors.margins: 3
        contentWidth: tabRow.implicitWidth
        contentHeight: height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick

        RowLayout {
            id: tabRow
            height: parent.height
            spacing: MichiSpacing.xs

            Repeater {
                id: tabRepeater
                model: root.tabs
                delegate: TabButton {
                    id: tabButton
                    required property int index
                    required property var modelData
                    Layout.preferredHeight: tabRow.height
                    Layout.preferredWidth: tabContent.implicitWidth + MichiSpacing.md * 2
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
                            Layout.preferredWidth: 18
                            Layout.preferredHeight: 18
                            name: tabButton.modelData.icon
                            iconColor: tabButton.checked
                                ? MichiPalette.auroraCyan
                                : tabButton.hovered
                                    ? MichiPalette.textPrimary
                                    : MichiPalette.textSecondary
                            strokeWidth: tabButton.checked ? 2.0 : 1.7
                        }
                        MichiText {
                            text: tabButton.text
                            role: "body"
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

                        Behavior on color {
                            enabled: !MichiAccessibility.reducedMotion
                            ColorAnimation { duration: MichiMotion.micro }
                        }
                        MichiFocusRing { visualFocus: tabButton.visualFocus }
                    }
                    onClicked: root.tabRequested(modelData.value)
                }
            }
        }
    }
}
