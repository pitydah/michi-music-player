import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: albumTimeline
    objectName: "albumTimelineView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.timelineAlbums
    clip: true
    section.property: "decade"
    section.criteria: ViewSection.FullString
    section.delegate: Text {
        width: albumTimeline.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: section
        font.pixelSize: MichiTheme.fontSizeCaption
        font.weight: MichiTheme.fontWeightBold
        color: MichiTheme.warning
        padding: MichiTheme.space8
    }
    delegate: RowLayout {
        width: albumTimeline.width
        height: MichiTheme.controlHeightSmall
        spacing: MichiTheme.space8

        Image {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
            visible: modelData.hasArtwork
            fillMode: Image.PreserveAspectFit
        }

        Text {
            Layout.fillWidth: true
            text: modelData.title
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textPrimary
            elide: Text.ElideRight
        }

        Text {
            text: modelData.year > 0 ? "" + modelData.year : "Unknown"
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: library.select_album(modelData.key)
        }
    }
}
