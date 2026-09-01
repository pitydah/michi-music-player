import QtQuick
import "../src/michi/presentation/qml/playlists"

// QA harness: el DetailView en producción vive dentro de ContentHost que
// le expone `parent.appearance` — el harness replica ese contrato.
Item {
    id: host
    width: 1200
    height: 900

    property var appearance: ({
        heroSolidColor: "#152A45",
        heroGradientColors: ["#152A45", "#13243D"],
        heroGradientAngle: 135,
        effectiveHeroImagePath: "",
        heroFocalX: 0.5,
        heroFocalY: 0.5
    })

    PlaylistDetailView {
        id: detail
        anchors.fill: parent
        objectName: "qaDetailView"
        playlistId: "qa-1"
    }
}
