import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Radio Station Detail"
    objectName: "radioStationDetail"
    focus: true
    id: root

    property var stationData: null
    property bool _isFav: stationData ? stationData.favorite : false

    signal playRequested()
    signal toggleFavRequested()
    signal editRequested()
    signal deleteRequested()

    implicitHeight: 70

    GlassCard {
        width: parent.width; height: root.implicitHeight
        title: root.stationData ? root.stationData.name || "" : ""
        subtitle: root.stationData
            ? [root.stationData.codec, root.stationData.country, root.stationData.bitrate ? root.stationData.bitrate + "kbps" : ""]
                .filter(function(x) { return x && x !== "" }).join(" · ")
            : ""

        RowLayout {
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.xs

            MichiIconButton {
                iconSource: "qrc:/icons/warm_play.svg"
                btnSize: 32
                tooltipText: "Reproducir"
                accessibleName: "Reproducir emisora"
                activeFocusOnTab: true
                onClicked: root.playRequested()
            }

            MichiButton {
                text: root._isFav ? "\u2605" : "\u2606"
                variant: "ghost"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                Accessible.name: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                activeFocusOnTab: true
                onClicked: root.toggleFavRequested()
            }

            MichiButton {
                text: "\u270E"
                variant: "ghost"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: "Editar"
                visible: true
                Accessible.name: "Editar emisora"
                activeFocusOnTab: true
                onClicked: root.editRequested()
            }

            MichiButton {
                text: "\u2716"
                variant: "danger"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: "Eliminar"
                Accessible.name: "Eliminar emisora"
                activeFocusOnTab: true
                onClicked: root.deleteRequested()
            }
        }
    }
}
