import QtQuick
import "../theme"

QtObject {
    id: root
    property string role: MichiMaterialRole.content

    readonly property bool blurEligible: role === MichiMaterialRole.elevated
        || role === MichiMaterialRole.hero
        || role === MichiMaterialRole.modal
    readonly property bool textured: role !== MichiMaterialRole.backplane
        && role !== MichiMaterialRole.control
    readonly property bool shadowed: role === MichiMaterialRole.elevated
        || role === MichiMaterialRole.hero || role === MichiMaterialRole.modal
    readonly property real textureOpacity: role === MichiMaterialRole.editorial ? 0.28
        : role === MichiMaterialRole.vinyl ? 0.18
        : role === MichiMaterialRole.content ? 0.12 : 0.2
    readonly property string textureName: role === MichiMaterialRole.editorial
        ? "paper-editorial-01" : role === MichiMaterialRole.vinyl
            ? "grain-graphite-02" : role === MichiMaterialRole.hero
                || role === MichiMaterialRole.modal ? "grain-glass-01"
                : "grain-graphite-01"
    readonly property color baseColor: role === MichiMaterialRole.backplane
        ? MichiPalette.obsidian : role === MichiMaterialRole.control
            ? MichiPalette.smoke : role === MichiMaterialRole.editorial
                ? MichiPalette.editorialPaper : role === MichiMaterialRole.vinyl
                    ? MichiPalette.vinylInner : role === MichiMaterialRole.modal
                        ? MichiPalette.smokeRaised : role === MichiMaterialRole.hero
                            ? MichiPalette.obsidianDeep : MichiPalette.obsidianRaised
    readonly property color bottomColor: role === MichiMaterialRole.vinyl
        ? MichiPalette.vinylMid : role === MichiMaterialRole.editorial
            ? MichiPalette.graphite : role === MichiMaterialRole.selected
                ? MichiPalette.smokeRaised : baseColor
}
