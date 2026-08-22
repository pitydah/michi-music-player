import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property string message: "Loading…"
    implicitHeight: 120
    ColumnLayout {
        anchors.centerIn: parent
        spacing: MichiSpacing.md
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: MichiSpacing.xs
            Repeater {
                model: 3
                Rectangle {
                    width: 5; height: 5; radius: 3
                    color: index === 1 ? MichiPalette.auroraCyan : MichiPalette.auroraBlue
                    opacity: 0.35
                    SequentialAnimation on opacity {
                        running: !MichiAccessibility.reducedMotion && root.visible
                        loops: Animation.Infinite
                        PauseAnimation { duration: index * 90 }
                        NumberAnimation { to: 1; duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                        NumberAnimation { to: 0.35; duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                        PauseAnimation { duration: (2 - index) * 90 }
                    }
                }
            }
        }
        MichiText { text: root.message; role: "secondary" }
    }
}
