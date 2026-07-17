import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property int volume: 80
    property bool muted: false
    property bool volumeSupported: true
    property bool muteSupported: true

    signal volumeAdjusted(int vol)
    signal muteClicked()

    implicitHeight: 38
    implicitWidth: 140

    Accessible.name: "Volumen"
    Accessible.description: "Control de volumen de reproducción"

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        Item {
            Layout.preferredWidth: 38
            Layout.preferredHeight: 38

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: volMa.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent"

                Image {
                    anchors.centerIn: parent
                    source: {
                        if (root.muted || root.volume === 0) return "qrc:/icons/nowplaying_clean/warm_mute_32.png"
                        if (root.volume < 40) return "qrc:/icons/nowplaying_clean/warm_vol_low_32.png"
                        if (root.volume < 70) return "qrc:/icons/nowplaying_clean/warm_vol_medium_32.png"
                        return "qrc:/icons/nowplaying_clean/warm_vol_high_32.png"
                    }
                    sourceSize.width: 22
                    sourceSize.height: 22
                    fillMode: Image.PreserveAspectFit
                    opacity: root.volumeSupported ? 1.0 : 0.35
                }

                MouseArea {
                    id: volMa
                    anchors.fill: parent
                    hoverEnabled: root.muteSupported
                    cursorShape: root.muteSupported ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: { if (root.muteSupported) root.muteClicked() }
                }

                Accessible.role: Accessible.Button
                Accessible.name: root.muted ? "Activar sonido" : "Silenciar"
                activeFocusOnTab: root.muteSupported
                Keys.onSpacePressed: root.muteClicked()
                Keys.onReturnPressed: root.muteClicked()
            }
        }

        MichiWarmSlider {
            id: volSlider
            Layout.preferredWidth: 88
            Layout.alignment: Qt.AlignVCenter
            from: 0
            to: 100
            value: root.muted ? 0 : root.volume
            enabled: root.volumeSupported
            onValueChanged: { if (pressed) root.volumeAdjusted(value) }
            onCommit: root.volumeAdjusted(value)

            WheelHandler {
                onWheel: function(event) {
                    var delta = event.angleDelta.y > 0 ? 5 : -5
                    var newVol = Math.max(0, Math.min(100, volSlider.value + delta))
                    volSlider.value = newVol
                    root.volumeAdjusted(newVol)
                }
            }
        }
    }
}
