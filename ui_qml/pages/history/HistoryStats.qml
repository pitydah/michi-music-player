import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "History Stats"
    objectName: "historyStats"
    focus: true
    id: root

    property int totalCount: 0
    property int completedCount: 0
    property int skippedCount: 0
    property int uniqueTracks: 0
    property int uniqueArtists: 0
    property string topArtist: ""
    property string topAlbum: ""
    property string periodDays: "30"

    implicitHeight: 120

    Row {
        anchors.fill: parent; spacing: MichiTheme.spacing.md

        GlassCard {
            width: (parent.width - MichiTheme.spacing.md * 3) / 4; height: 100
            title: root.totalCount.toString(); subtitle: qsTr("Total reproducciones")
        }
        GlassCard {
            width: (parent.width - MichiTheme.spacing.md * 3) / 4; height: 100
            title: root.uniqueTracks.toString(); subtitle: qsTr("Pistas únicas")
        }
        GlassCard {
            width: (parent.width - MichiTheme.spacing.md * 3) / 4; height: 100
            title: root.uniqueArtists.toString(); subtitle: qsTr("Artistas")
        }
        GlassCard {
            width: (parent.width - MichiTheme.spacing.md * 3) / 4; height: 100
            title: root.topArtist || "—"; subtitle: qsTr("Artista principal")
        }
    }
}
