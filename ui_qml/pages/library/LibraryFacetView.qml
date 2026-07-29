import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

StackLayout {
    id: root
    objectName: "libraryFacetView"

    property var entries: []
    property int currentView: 0
    property string singularName: qsTr("elemento")
    property string pluralName: qsTr("elementos")
    property string iconKey: "songs"
    property bool hasMore: false
    property bool loadingMore: false

    signal entryActivated(string value)
    signal fetchMoreRequested()

    function maybeFetchMore(view) {
        if (!root.hasMore || root.loadingMore || !view || view.moving)
            return
        var remaining = view.contentHeight - (view.contentY + view.height)
        if (remaining <= Math.max(160, view.height * 0.35))
            root.fetchMoreRequested()
    }

    function labelOf(entry) {
        if (typeof entry !== "object")
            return entry || ""
        return entry.name || entry.genre || entry.composer || ""
    }

    function countOf(entry) {
        if (typeof entry !== "object")
            return 0
        return Number(entry.count || entry.track_count || entry.trackCount) || 0
    }

    currentIndex: root.currentView

    GridView {
        id: facetGrid
        objectName: "libraryFacetGrid"
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: root.entries
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        focus: true
        cacheBuffer: cellHeight * 2
        leftMargin: MichiTheme.spacing.xs
        rightMargin: MichiTheme.spacing.xs
        onMovementEnded: root.maybeFetchMore(facetGrid)
        onContentYChanged: gridFetchTimer.restart()

        Timer {
            id: gridFetchTimer
            interval: 90
            repeat: false
            onTriggered: root.maybeFetchMore(facetGrid)
        }

        readonly property int minimumCellWidth: 220
        readonly property int columns: Math.max(1, Math.floor(width / minimumCellWidth))
        cellWidth: width / columns
        cellHeight: 104

        Keys.onReturnPressed: {
            if (currentIndex >= 0 && currentIndex < root.entries.length)
                root.entryActivated(root.labelOf(root.entries[currentIndex]))
        }
        Keys.onEnterPressed: {
            if (currentIndex >= 0 && currentIndex < root.entries.length)
                root.entryActivated(root.labelOf(root.entries[currentIndex]))
        }

        ScrollBar.vertical: ScrollBar {
            width: 8
            policy: ScrollBar.AsNeeded
        }

        delegate: Item {
            id: gridDelegate
            required property int index
            required property var modelData
            readonly property bool selected: GridView.isCurrentItem

            width: facetGrid.cellWidth
            height: facetGrid.cellHeight

            Rectangle {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xs
                radius: MichiTheme.radius.lg
                color: gridMouse.pressed
                       ? MichiTheme.colors.surfacePressed
                       : gridDelegate.selected
                         ? MichiTheme.colors.accentSelection
                         : gridMouse.containsMouse
                           ? MichiTheme.colors.surfaceCardHover
                           : MichiTheme.colors.surfaceCard
                border.width: gridDelegate.selected || gridMouse.containsMouse
                              ? MichiTheme.borderWidth : 0
                border.color: gridDelegate.selected
                              ? MichiTheme.colors.borderActive
                              : MichiTheme.colors.borderHover

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.md
                    spacing: MichiTheme.spacing.md

                    Rectangle {
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 44
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceElevation3
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderInner

                        MichiIcon {
                            anchors.centerIn: parent
                            iconKey: root.iconKey
                            size: 21
                            color: gridDelegate.selected
                                   ? MichiTheme.colors.accentBlue
                                   : MichiTheme.colors.textSecondary
                            accessibleName: ""
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            Layout.fillWidth: true
                            text: root.labelOf(gridDelegate.modelData)
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.countOf(gridDelegate.modelData) > 0
                                  ? qsTr("%1 canciones").arg(
                                        root.countOf(gridDelegate.modelData)
                                    )
                                  : qsTr("Abrir %1").arg(root.singularName)
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            elide: Text.ElideRight
                        }
                    }
                }

                MouseArea {
                    id: gridMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onPressed: facetGrid.currentIndex = gridDelegate.index
                    onClicked: root.entryActivated(
                                   root.labelOf(gridDelegate.modelData)
                               )
                }
            }
        }
    }

    ListView {
        id: facetList
        objectName: "libraryFacetList"
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: root.entries
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        focus: true
        spacing: 2
        leftMargin: MichiTheme.spacing.xs
        rightMargin: MichiTheme.spacing.xs
        onMovementEnded: root.maybeFetchMore(facetList)
        onContentYChanged: listFetchTimer.restart()

        Timer {
            id: listFetchTimer
            interval: 90
            repeat: false
            onTriggered: root.maybeFetchMore(facetList)
        }

        Keys.onReturnPressed: {
            if (currentIndex >= 0 && currentIndex < root.entries.length)
                root.entryActivated(root.labelOf(root.entries[currentIndex]))
        }
        Keys.onEnterPressed: {
            if (currentIndex >= 0 && currentIndex < root.entries.length)
                root.entryActivated(root.labelOf(root.entries[currentIndex]))
        }

        ScrollBar.vertical: ScrollBar {
            width: 8
            policy: ScrollBar.AsNeeded
        }

        delegate: Rectangle {
            id: listDelegate
            required property int index
            required property var modelData

            width: facetList.width
            height: 44
            radius: MichiTheme.radius.sm
            color: listMouse.pressed
                   ? MichiTheme.colors.surfacePressed
                   : ListView.isCurrentItem
                     ? MichiTheme.colors.accentSelection
                     : listMouse.containsMouse
                       ? MichiTheme.colors.surfaceHover
                       : "transparent"
            border.width: ListView.isCurrentItem ? MichiTheme.borderWidth : 0
            border.color: MichiTheme.colors.borderActive

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.md

                MichiIcon {
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 18
                    iconKey: root.iconKey
                    size: 18
                    color: ListView.isCurrentItem
                           ? MichiTheme.colors.accentBlue
                           : MichiTheme.colors.textMuted
                    accessibleName: ""
                }

                Text {
                    Layout.fillWidth: true
                    text: root.labelOf(listDelegate.modelData)
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: ListView.isCurrentItem
                                 ? MichiTheme.typography.weightSemiBold
                                 : MichiTheme.typography.weightNormal
                    elide: Text.ElideRight
                }

                Text {
                    text: root.countOf(listDelegate.modelData) > 0
                          ? qsTr("%1 canciones").arg(
                                root.countOf(listDelegate.modelData)
                            )
                          : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            MouseArea {
                id: listMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onPressed: facetList.currentIndex = listDelegate.index
                onClicked: root.entryActivated(
                               root.labelOf(listDelegate.modelData)
                           )
            }
        }
    }
}
