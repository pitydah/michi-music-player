import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root

    property string formatKey: "unknown"
    property string displayLabel: "UNKNOWN"

    readonly property string family: {
        if (["flac", "wav", "aiff", "aif", "alac", "ape", "wavpack"].indexOf(formatKey) !== -1)
            return "cyan"
        if (["mp3", "aac", "m4a", "wma"].indexOf(formatKey) !== -1)
            return "blue"
        if (["ogg", "opus"].indexOf(formatKey) !== -1)
            return "purple-soft"
        if (["dsf", "dff"].indexOf(formatKey) !== -1)
            return "purple"
        return "neutral"
    }

    implicitWidth: label.implicitWidth + MichiSpacing.sm * 2
    implicitHeight: 24
    radius: MichiRadius.sm
    color: family === "cyan" ? MichiSemanticColors.auroraCyanSurface
        : family === "purple" ? MichiSemanticColors.auroraPurpleSurface
        : family === "purple-soft" ? MichiSemanticColors.auroraPurpleSurfaceSoft
        : MichiSemanticColors.controlSurface
    border.width: 1
    border.color: family === "cyan" ? MichiSemanticColors.auroraCyanBorderSubtle
        : family === "blue" ? MichiSemanticColors.auroraBorderSubtle
        : family === "purple" ? MichiSemanticColors.auroraPurpleBorder
        : family === "purple-soft" ? MichiSemanticColors.auroraPurpleBorderSoft
        : MichiSemanticColors.borderSubtle
    Accessible.role: Accessible.StaticText
    Accessible.name: qsTr("Format: %1").arg(displayLabel)

    MichiText {
        id: label
        anchors.centerIn: parent
        text: root.displayLabel
        role: "technical"
        technical: true
        font.weight: Font.DemiBold
        color: root.family === "cyan" ? MichiPalette.auroraCyan
            : root.family === "blue" ? MichiPalette.auroraBlue
            : root.family.indexOf("purple") === 0 ? MichiPalette.auroraPurple
            : MichiPalette.textSecondary
    }
}
