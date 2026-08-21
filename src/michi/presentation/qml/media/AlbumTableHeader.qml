import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property bool showArtist: true
    property bool showYear: true
    property bool showTrackCount: true
    property bool showDuration: true
    property bool showTechnical: MichiThemeState.precisionMode
    property string sortMode: "title"
    signal sortRequested(string mode)

    implicitHeight: MichiMetrics.controlMedium
    color: MichiSemanticColors.controlSurfaceStrong
    border.width: 1
    border.color: MichiSemanticColors.borderSubtle
    radius: MichiRadius.sm
    z: 10

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md
        Item {
            Layout.preferredWidth: MichiThemeState.density === "comfortable" ? 40 : 34
        }
        MichiText {
            Layout.fillWidth: true
            text: "ALBUM"
            role: "technical"
            technical: true
            color: root.sortMode === "title"
                ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showArtist
            Layout.preferredWidth: 170
            text: "ALBUM ARTIST"
            role: "technical"
            technical: true
            color: root.sortMode === "artist"
                ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showYear
            Layout.preferredWidth: 54
            text: "YEAR"
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
            color: root.sortMode === "year"
                ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showTrackCount
            Layout.preferredWidth: 48
            text: "TRACKS"
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
            color: root.sortMode === "tracks"
                ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showDuration
            Layout.preferredWidth: 58
            text: "TIME"
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
            color: root.sortMode === "duration"
                ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showTechnical
            Layout.preferredWidth: 160
            text: "FORMAT"
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
    }
}
