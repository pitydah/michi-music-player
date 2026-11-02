import QtQuick
import "../primitives"
import "../theme"

// Small, non-interactive Signal Truth indicator. The dot is never a quality
// claim: it follows the bridge's observed state, and the accessible name
// carries the full explanation.
Item {
    id: root
    property string indicatorState: "none"
    property string tooltip: qsTr("Signal Truth: no active playback")
    implicitWidth: 14
    implicitHeight: 14

    readonly property color stateColor: root.indicatorState === "observed"
        ? MichiPalette.success
        : root.indicatorState === "transformed" ? MichiPalette.auroraCyan
        : root.indicatorState === "pending" ? MichiPalette.auroraBlue
        : root.indicatorState === "historical" ? MichiPalette.textSecondary
        : root.indicatorState === "error" ? MichiPalette.error
        : MichiPalette.textMuted
    readonly property string glyphName: root.indicatorState === "observed"
        ? "check"
        : root.indicatorState === "transformed" ? "equalizer"
        : root.indicatorState === "historical" ? "history"
        : root.indicatorState === "error" ? "info"
        : root.indicatorState === "pending" ? "history"
        : ""

    Accessible.role: Accessible.StaticText
    Accessible.name: root.tooltip
    Accessible.ignored: root.indicatorState === "none"

    Rectangle {
        anchors.centerIn: parent
        width: 14
        height: 14
        radius: 7
        color: root.indicatorState === "none"
            ? "transparent" : MichiSemanticColors.statusSurface(root.stateColor)
        border.width: root.indicatorState === "none" ? 0 : 1
        border.color: root.stateColor

        MichiIcon {
            visible: root.glyphName !== ""
            anchors.centerIn: parent
            name: root.glyphName
            width: 8
            height: 8
            iconColor: root.stateColor
        }

        Rectangle {
            visible: root.indicatorState === "none"
            anchors.centerIn: parent
            width: 7
            height: 7
            radius: 4
            color: MichiPalette.textMuted
        }
    }
}
