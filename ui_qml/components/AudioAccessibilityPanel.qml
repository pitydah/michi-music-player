import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Accessibility"
    objectName: "audioAccessibilityPanel"
    focus: true
    id: root

    property var audioBridge: null
    property var themeBridge: null
    property bool monoEnabled: false
    property real balance: 0.0
    property bool reduceMotion: false



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
        }

        ErrorAnnouncement {
            id: errorAnnouncement
        }

        PlaybackStateAnnouncement {
            id: playbackAnnouncement
        }
    }
}
