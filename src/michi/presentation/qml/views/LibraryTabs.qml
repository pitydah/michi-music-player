import QtQuick
import QtQuick.Layouts
import "../theme"

RowLayout {
    property string currentTab: "songs"

    Layout.fillWidth: true
    spacing: MichiTheme.space12

    Text {
        text: "Songs"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "songs" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "songs" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "songs"
        }
    }

    Text {
        text: "Albums"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "albums" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "albums" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "albums"
        }
    }

    Text {
        text: "Artists"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "artists" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "artists" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "artists"
        }
    }

    Text {
        text: "Genres"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "genres" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "genres" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "genres"
        }
    }

    Text {
        text: "Folders"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "folders" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "folders" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "folders"
        }
    }

    Text {
        text: "Favorites"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "favorites" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "favorites" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "favorites"
        }
    }

    Text {
        text: "History"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "history" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "history" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "history"
        }
    }

    Text {
        text: "Recently Added"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "recently" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "recently" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "recently"
        }
    }

    Text {
        text: "Playlists"
        font.pixelSize: MichiTheme.fontSizeBody
        font.weight: currentTab === "playlists" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
        color: currentTab === "playlists" ? MichiTheme.warning : MichiTheme.textSecondary
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: currentTab = "playlists"
        }
    }
}
