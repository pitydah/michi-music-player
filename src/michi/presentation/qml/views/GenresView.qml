import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../theme"

// GenresView — canonical Genre navigation. Genre.key is identity; a display
// name is never substituted as a search query for an exact entity intent.
ListView {
    id: root
    objectName: "genresView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.genres
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    activeFocusOnTab: true

    ScrollBar.vertical: MichiScrollBar { }

    header: EmptyState {
        width: root.width
        height: root.height
        visible: root.count === 0
        title: qsTr("No genres found")
        message: qsTr("Scan a music folder to build genre navigation.")
        iconName: "genre"
    }

    delegate: MichiEntityRow {
        id: genreRow
        required property int index
        required property var modelData
        width: root.width
        iconName: "genre"
        title: modelData.name
        technical: modelData.trackCount + (modelData.trackCount === 1 ? " track" : " tracks")
        interactive: true
        onActivated: library.select_genre(modelData.key)
        Keys.onPressed: event => genreContext.handleContextKey(event)

        GenreContextArea {
            id: genreContext
            anchors.fill: parent
            genre: modelData
            onContextRequested: {
                root.currentIndex = genreRow.index
                genreRow.forceActiveFocus()
            }
        }
    }
}
