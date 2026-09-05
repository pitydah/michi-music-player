import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Item {
    id: root

    property string currentTab: "songs"
    signal tabRequested(string tab)
    readonly property var tabs: [
        { value: "songs", label: qsTr("Songs"), icon: "track" },
        { value: "albums", label: qsTr("Albums"), icon: "album" },
        { value: "artists", label: qsTr("Artists"), icon: "artist" },
        { value: "genres", label: qsTr("Genres"), icon: "genre" },
        { value: "favorites", label: qsTr("Favorites"), icon: "heart" },
        { value: "history", label: qsTr("History"), icon: "history" },
        { value: "recently", label: qsTr("Recently Added"), icon: "recent" }
    ]
    readonly property real overflowButtonWidth: 28
    // Use the unreserved root width for the decision so the edge controls do
    // not create a self-referential overflow toggle.
    readonly property bool overflowed: tabRow.implicitWidth > root.width - 6

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

    function clampContentX(value) {
        return Math.max(0, Math.min(
            Math.max(0, navigationFlickable.contentWidth - navigationFlickable.width),
            value))
    }

    function scrollTabs(delta) {
        navigationFlickable.contentX = root.clampContentX(
            navigationFlickable.contentX + delta)
    }

    function ensureCurrentTabVisible() {
        for (var index = 0; index < tabRepeater.count; index++) {
            var item = tabRepeater.itemAt(index)
            if (!item || root.tabs[index].value !== root.currentTab)
                continue
            var leftEdge = item.x
            var rightEdge = item.x + item.width
            if (leftEdge < navigationFlickable.contentX)
                navigationFlickable.contentX = root.clampContentX(leftEdge)
            else if (rightEdge > navigationFlickable.contentX + navigationFlickable.width)
                navigationFlickable.contentX = root.clampContentX(
                    rightEdge - navigationFlickable.width)
            return
        }
    }

    onCurrentTabChanged: Qt.callLater(root.ensureCurrentTabVisible)
    onWidthChanged: Qt.callLater(root.ensureCurrentTabVisible)
    onOverflowedChanged: Qt.callLater(root.ensureCurrentTabVisible)

    Flickable {
        id: navigationFlickable
        anchors.fill: parent
        anchors.topMargin: 3
        anchors.bottomMargin: 3
        anchors.leftMargin: root.overflowed ? root.overflowButtonWidth : 3
        anchors.rightMargin: root.overflowed ? root.overflowButtonWidth : 3
        contentWidth: tabRow.implicitWidth
        contentHeight: height
        clip: true
        interactive: root.overflowed
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
                    // Historical premium tabs used generous padding, but at
                    // real Library widths that clipped Recently Added.  Keep
                    // the same hierarchy with a tighter, still-comfortable hitbox.
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

    // Overflow is intentional and discoverable rather than looking like a
    // clipped first/last tab.  The controls reserve stable edge gutters while
    // overflow exists, so changing currentTab never makes the strip jump.
    Button {
        id: leftOverflowButton
        objectName: "libraryTabsScrollLeft"
        visible: root.overflowed
        enabled: navigationFlickable.contentX > 0.5
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.verticalCenter: parent.verticalCenter
        width: root.overflowButtonWidth - 2
        height: MichiMetrics.controlMedium
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        Accessible.role: Accessible.Button
        Accessible.name: qsTr("Show previous library tabs")
        onClicked: root.scrollTabs(-Math.max(140, navigationFlickable.width * 0.55))
        contentItem: MichiText {
            text: "‹"
            role: "section"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            color: leftOverflowButton.enabled
                ? MichiPalette.textSecondary : MichiPalette.textDisabled
        }
        background: Rectangle {
            radius: MichiRadius.md
            color: leftOverflowButton.pressed
                ? MichiSemanticColors.surfacePressed
                : leftOverflowButton.hovered && leftOverflowButton.enabled
                    ? MichiSemanticColors.surfaceHover : MichiPalette.smoke
            border.width: 1
            border.color: leftOverflowButton.hovered && leftOverflowButton.enabled
                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
            opacity: leftOverflowButton.enabled ? 1 : 0.45
        }
    }

    Button {
        id: rightOverflowButton
        objectName: "libraryTabsScrollRight"
        visible: root.overflowed
        enabled: navigationFlickable.contentX
            < Math.max(0, navigationFlickable.contentWidth - navigationFlickable.width) - 0.5
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.verticalCenter: parent.verticalCenter
        width: root.overflowButtonWidth - 2
        height: MichiMetrics.controlMedium
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        Accessible.role: Accessible.Button
        Accessible.name: qsTr("Show more library tabs")
        onClicked: root.scrollTabs(Math.max(140, navigationFlickable.width * 0.55))
        contentItem: MichiText {
            text: "›"
            role: "section"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            color: rightOverflowButton.enabled
                ? MichiPalette.textSecondary : MichiPalette.textDisabled
        }
        background: Rectangle {
            radius: MichiRadius.md
            color: rightOverflowButton.pressed
                ? MichiSemanticColors.surfacePressed
                : rightOverflowButton.hovered && rightOverflowButton.enabled
                    ? MichiSemanticColors.surfaceHover : MichiPalette.smoke
            border.width: 1
            border.color: rightOverflowButton.hovered && rightOverflowButton.enabled
                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
            opacity: rightOverflowButton.enabled ? 1 : 0.45
        }
    }
}
