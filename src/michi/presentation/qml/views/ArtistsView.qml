import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

Item {
    id: root
    objectName: "artistsView"
    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true

    ListView {
        id: artistList
        anchors.fill: parent
        visible: library.selectedArtistKey === ""
        model: library.artists
        clip: true
        spacing: MichiSpacing.xs
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: true

        delegate: MichiEntityRow {
            required property var modelData
            width: artistList.width
            iconName: "artist"
            title: modelData.name
            subtitle: modelData.albumCount + " albums"
            technical: modelData.trackCount + " tracks"
            onActivated: library.select_artist(modelData.key)
        }
    }

    ArtistDetailView {
        anchors.fill: parent
        addTargetPath: root.addTargetPath
        onAddTargetPathChanged: root.addTargetPath = addTargetPath
    }
}
