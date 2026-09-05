import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../theme"

// Visible-recovery pass: Genre is a real Library surface, never a blank
// viewport.  The old ListView.header empty-state reserved root.height even
// when invisible, which could push every productive delegate below the view.
Item {
    id: root
    objectName: "genresView"

    Layout.fillWidth: true
    Layout.fillHeight: true

    ListView {
        id: genreList
        anchors.fill: parent
        model: library.genres
        visible: count > 0
        clip: true
        spacing: MichiSpacing.xs
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: true
        keyNavigationWraps: false
        activeFocusOnTab: true

        ScrollBar.vertical: MichiScrollBar { }

        delegate: MichiEntityRow {
            id: genreRow
            required property int index
            required property var modelData
            width: genreList.width
            iconName: "genre"
            title: modelData.name
            technical: qsTr("%n track(s)", "", Number(modelData.trackCount || 0))
            interactive: true
            onActivated: library.select_genre(modelData.key)
            Keys.onPressed: event => genreContext.handleContextKey(event)

            GenreContextArea {
                id: genreContext
                anchors.fill: parent
                genre: modelData
                onContextRequested: {
                    genreList.currentIndex = genreRow.index
                    genreRow.forceActiveFocus()
                }
            }
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: genreList.count === 0
        title: library.searchActive
            ? qsTr("No matching genres") : qsTr("No genres found")
        message: library.searchActive
            ? qsTr("Try a broader search or clear the current query.")
            : qsTr("Scan a music folder to build genre navigation.")
        iconName: "genre"
    }
}
