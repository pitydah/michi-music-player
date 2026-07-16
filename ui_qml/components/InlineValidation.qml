import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Inline Validation"
    objectName: "inlineValidation"
    focus: true
    id: root

    enum Variant {
        ERROR,
        WARNING,
        SUCCESS,
        INFO
    }

    property int variant: InlineValidation.ERROR
    property string message: ""
    property bool dismissible: false
    signal dismissed()

    implicitHeight: visible ? layout.implicitHeight + MichiTheme.spacing.sm * 2 : 0
    radius: MichiTheme.radiusSm
    visible: message !== ""


    color: {
        switch (root.variant) {
            case InlineValidation.ERROR: return MichiTheme.colors.badgeDangerBg
            case InlineValidation.WARNING: return MichiTheme.colors.badgeWarningBg
            case InlineValidation.SUCCESS: return MichiTheme.colors.badgeActiveBg
            default: return MichiTheme.colors.badgeInfoBg
        }
    }

    border.width: 0

    Behavior on implicitHeight {
        NumberAnimation {
            duration: MichiTheme.motion.fast
            easing.type: Easing.OutCubic
        }
    }

    Row {
        id: layout
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.sm
        anchors.rightMargin: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.xs

        Text {
            text: {
                switch (root.variant) {
                    case InlineValidation.ERROR: return "\u2716"
                    case InlineValidation.WARNING: return "\u26A0"
                    case InlineValidation.SUCCESS: return "\u2714"
                    default: return "\u2139"
                }
            }
            color: {
                switch (root.variant) {
                    case InlineValidation.ERROR: return MichiTheme.colors.error
                    case InlineValidation.WARNING: return MichiTheme.colors.warning
                    case InlineValidation.SUCCESS: return MichiTheme.colors.success
                    default: return MichiTheme.colors.accentBlue
                }
            }
            font.pixelSize: MichiTheme.typography.bodySize
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            text: root.message
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            width: parent.width - 36
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            text: "\u2715"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            visible: root.dismissible
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    root.message = ""
                    root.dismissed()
                }
            }
        }
    }
}
