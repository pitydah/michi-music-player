import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var stationData: null
    property bool _isFav: stationData ? stationData.favorite : false

    signal play()
    signal toggleFav()
    signal edit()
    signal delete()

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

            MichiButton {
                text: "\u25B6"
                variant: "ghost"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: "Reproducir"
                onClicked: root.play()
            }

            MichiButton {
                text: root._isFav ? "\u2605" : "\u2606"
                variant: "ghost"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                onClicked: root.toggleFav()
            }

            MichiButton {
                text: "\u270E"
                variant: "ghost"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: "Editar"
                visible: true
                onClicked: root.edit()
            }

            MichiButton {
                text: "\u2716"
                variant: "danger"
                implicitWidth: 32; implicitHeight: 32
                tooltipText: "Eliminar"
                onClicked: root.delete()
            }
        }
    }
}
