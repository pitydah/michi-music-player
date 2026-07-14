import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root

    property var audioBridge: null
    property var themeBridge: null
    property bool monoEnabled: false
    property real balance: 0.0
    property bool reduceMotion: false

    objectName: "audioAccessibilityPanel"

    Accessible.role: Accessible.Grouping
    Accessible.name: "Panel de accesibilidad de audio"

    implicitWidth: column.implicitWidth
    implicitHeight: column.implicitHeight

    Column {
        id: column
        spacing: MichiTheme.spacing.md

        Text {
            text: "Accesibilidad de audio"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            Accessible.name: "Accesibilidad de audio"
        }

        MonoToggle {
            id: monoToggle
            monoEnabled: root.monoEnabled
            audioBridge: root.audioBridge
            onMonoToggled: function(enabled) {
                root.monoEnabled = enabled
            }
        }

        BalanceSlider {
            id: balanceSlider
            balance: root.balance
            audioBridge: root.audioBridge
            onBalanceChanged: function(value) {
                root.balance = value
            }
        }

        ReducedMotionToggle {
            id: reducedMotionToggle
            reduceMotion: root.reduceMotion
            themeBridge: root.themeBridge
            onReduceMotionToggled: function(enabled) {
                root.reduceMotion = enabled
            }
        }

        NotificationAnnouncement {
            id: announcement
            objectName: "accessibilityAnnouncement"
        }

        ErrorAnnouncement {
            id: errorAnnouncement
            objectName: "accessibilityErrorAnnouncement"
        }

        PlaybackStateAnnouncement {
            id: playbackAnnouncement
            objectName: "accessibilityPlaybackAnnouncement"
        }
    }
}
