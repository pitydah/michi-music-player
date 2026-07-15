import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string message: "Cancelando..."
    property string objectName: "cancellationState"

    Accessible.role: Accessible.Alert
    Accessible.name: root.message

    Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: 48
        color: MichiTheme.colors.error
        opacity: 0.9

        OpacityAnimator {
            target: root
            from: 0.7
            to: 1.0
            duration: MichiTheme.motion.normal
            running: true
        }

        Row {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.sm

            BusyIndicator {
                width: 20
                height: 20
                running: true
            }

            Text {
                text: root.message
                color: MichiTheme.colors.textOnError
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
