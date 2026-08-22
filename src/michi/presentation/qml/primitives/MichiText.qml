import QtQuick
import "../theme"

Text {
    id: root
    property string role: "body"
    property bool technical: false

    color: role === "muted" ? MichiPalette.textMuted
        : role === "secondary" || role === "technical" || role === "micro"
            ? MichiPalette.textSecondary
        : MichiPalette.textPrimary
    font.family: MichiTypography.family
    font.pixelSize: role === "display" ? MichiTypography.display
        : role === "title" ? MichiTypography.title
        : role === "section" ? MichiTypography.section
        : role === "caption" ? MichiTypography.caption
        : role === "technical" ? MichiTypography.technical
        : role === "micro" ? MichiTypography.micro
        : role === "secondary" ? MichiTypography.secondary
        : MichiTypography.body
    font.weight: role === "display" || role === "title" || role === "section"
        ? Font.DemiBold : Font.Normal
    font.letterSpacing: role === "display" ? -0.35
        : role === "title" ? -0.18
        : role === "technical" ? 0.22
        : role === "micro" ? 0.35 : 0
    font.features: (technical || role === "technical" || role === "caption" || role === "micro") ? ({ "tnum": 1 }) : ({})
    renderType: Text.NativeRendering
}
