import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

// GenresView — Audiophile Genre navigation with direct search filtering
ListView {
    id: root
    objectName: "genresView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.genres
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds

    delegate: MichiEntityRow {
        required property var modelData
        width: root.width
        iconName: "genre"
        title: modelData.name
        technical: modelData.trackCount + (modelData.trackCount === 1 ? " track" : " tracks")
        interactive: true
        onActivated: library.search(modelData.name)
    }
}
