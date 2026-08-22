import QtQuick
import QtQuick.Effects
import "../theme"

Item {
    id: root
    default property alias contentData: content.data
    property string elevation: "standard"
    property int contentPadding: MichiSpacing.lg
    property bool accented: false
    property bool accentLineVisible: false
    property color accentColor: MichiPalette.auroraBlue
    property bool shadowed: elevation !== "subtle"
    property bool textured: elevation !== "subtle"
    property int tileSeed: 0
    property real radius: elevation === "subtle"
        ? MichiRadius.md : MichiRadius.floating
    readonly property real materialOpacity: MichiThemeState.glassQuality === "low" ? 0.96
        : MichiThemeState.glassQuality === "high" ? 0.76 : 0.86
    readonly property bool raised: elevation === "modal" || elevation === "elevated"
    readonly property color materialTop: MichiSemanticColors.glassTop(
        root.raised, root.materialOpacity)
    readonly property color materialBottom: MichiSemanticColors.glassBottom(
        root.raised, root.materialOpacity)

    // Real backdrop blur (QtQuick.Effects) — only at high glass quality and
    // on non-subtle surfaces, where the render cost is justified. Falls back
    // to the tinted-gradient material otherwise (no window in tests → off).
    readonly property bool blurEnabled: MichiThemeState.glassQuality === "high"
        && root.elevation !== "subtle" && root.window !== null
    readonly property real blurAmount: root.elevation === "modal" ? MichiElevation.modalBlur
        : root.raised ? MichiElevation.elevatedBlur : MichiElevation.standardBlur

    Rectangle {
        visible: root.shadowed
        x: -MichiElevation.shadowFarSpread
        y: MichiElevation.shadowVerticalOffset
        width: root.width + MichiElevation.shadowFarSpread * 2
        height: root.height + MichiElevation.shadowFarSpread
        radius: root.radius + MichiElevation.shadowFarSpread
        color: MichiSemanticColors.glassShadowFar
        z: -2
    }

    Rectangle {
        visible: root.shadowed
        x: -MichiElevation.shadowNearSpread
        y: MichiElevation.shadowVerticalOffset / 2
        width: root.width + MichiElevation.shadowNearSpread * 2
        height: root.height + MichiElevation.shadowNearSpread * 2
        radius: root.radius + MichiElevation.shadowNearSpread
        color: MichiSemanticColors.glassShadowNear
        z: -1
    }

    Rectangle {
        id: material
        anchors.fill: parent
        radius: root.radius
        border.width: 1
        border.color: MichiAccessibility.highContrast
            ? MichiSemanticColors.borderStrong
            : root.accented ? MichiSemanticColors.accentBorder(root.accentColor)
            : root.raised ? MichiSemanticColors.borderStrong
            : MichiSemanticColors.borderSubtle
        clip: true

        // ── Backdrop blur: what lies behind the glass, blurred ──────────
        ShaderEffectSource {
            id: blurSource
            anchors.fill: parent
            visible: root.blurEnabled
            sourceItem: root.window
            sourceRect: Qt.rect(
                root.mapToItem(root.window, 0, 0).x,
                root.mapToItem(root.window, 0, 0).y,
                root.width, root.height)
            live: true
        }
        MultiEffect {
            id: blurEffect
            anchors.fill: parent
            visible: root.blurEnabled
            source: blurSource
            blur: root.blurAmount / MichiElevation.modalBlur
            blurMax: MichiElevation.modalBlur
            saturation: 0.9
        }

        // ── Tinted material: the glass color, over the blurred backdrop ──
        Rectangle {
            anchors.fill: parent
            color: root.materialBottom
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0; color: root.materialTop }
                GradientStop { position: 1; color: root.materialBottom }
            }
            opacity: root.blurEnabled ? 0.88 : 1
        }

        MichiMaterialTexture {
            anchors.fill: parent
            tileSeed: root.tileSeed
            visible: root.textured && opacity > 0
        }

        // ── Specular glint: the diagonal light catch that sells "glass" ──
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            width: Math.min(parent.width, parent.height) * 0.6
            height: width
            radius: width / 2
            gradient: Gradient {
                orientation: Gradient.Radial
                GradientStop { position: 0; color: MichiAccessibility.highContrast
                    ? MichiSemanticColors.glassGlintStrong : MichiSemanticColors.glassGlint }
                GradientStop { position: 1; color: "transparent" }
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, root.radius - 1)
            color: "transparent"
            border.width: 1
            border.color: MichiSemanticColors.glassInnerBorder
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 1
            anchors.rightMargin: 1
            anchors.topMargin: 1
            height: Math.min(parent.height * 0.5, 56)
            radius: Math.max(0, root.radius - 1)
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0; color: MichiSemanticColors.glassSheen }
                GradientStop { position: 1; color: "transparent" }
            }
        }

        Rectangle {
            visible: root.accented && root.accentLineVisible
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: root.radius
            anchors.rightMargin: root.radius
            height: 1
            color: root.accentColor
            opacity: MichiAccessibility.highContrast ? 0.9 : 0.42
        }

        // Glass rim: brighter top edge, darker bottom edge
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            radius: root.radius
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "transparent" }
                GradientStop { position: 0.25; color: MichiSemanticColors.innerHighlight }
                GradientStop { position: 0.75; color: MichiSemanticColors.innerHighlight }
                GradientStop { position: 1; color: "transparent" }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: root.radius
            anchors.rightMargin: root.radius
            height: 1
            color: MichiSemanticColors.glassShadow
        }
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.contentPadding
        z: 1
    }
}
