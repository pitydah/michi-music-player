import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import "../theme"

Item {
    id: root
    default property alias contentData: content.data
    property string elevation: "standard"
    property string materialRole: MichiMaterialRole.control
    property int contentPadding: MichiSpacing.lg
    property bool accented: false
    property bool accentLineVisible: false
    property color accentColor: MichiPalette.auroraBlue
    property bool shadowed: elevation !== "subtle"
    property bool textured: materialSpec.textured
    property int tileSeed: 0
    // none: clean material; edge: rim/sheens only; michi: subtle brand glint.
    // auto/always/never remain compatibility aliases for older call sites.
    property string glintMode: "none"
    // Always-on backdrop blur (true smoke glass) for hero surfaces like
    // the sidebar — overrides the high-quality-only gate.
    property bool forceBlur: false
    // Explicit material opacity override (0..1); -1 keeps the quality-based
    // default. Lower values make the glass more translucent.
    property real materialOpacityOverride: -1
    property real radius: elevation === "subtle"
        ? MichiRadius.md : MichiRadius.floating
    readonly property real materialOpacity: root.materialOpacityOverride >= 0
        ? root.materialOpacityOverride
        : MichiThemeState.glassQuality === "low" ? 0.96
        : MichiThemeState.glassQuality === "high" ? 0.76 : 0.86
    readonly property bool raised: elevation === "modal" || elevation === "elevated"
        || materialRole === MichiMaterialRole.elevated
        || materialRole === MichiMaterialRole.hero
        || materialRole === MichiMaterialRole.modal
    MichiMaterial { id: materialSpec; role: root.materialRole }
    readonly property color materialTop: MichiSemanticColors.glassTop(
        root.raised, root.materialOpacity)
    readonly property color materialBottom: MichiSemanticColors.glassBottom(
        root.raised, root.materialOpacity)

    // Real backdrop blur (QtQuick.Effects) — only at high glass quality and
    // on non-subtle surfaces, where the render cost is justified. Falls back
    // to the tinted-gradient material otherwise (no window in tests → off).
    readonly property bool blurEnabled: root.window !== null
        && (root.forceBlur
            || (materialSpec.blurEligible && MichiThemeState.glassQuality === "high"
                && root.elevation !== "subtle"))
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
            sourceItem: root.window ? root.window.contentItem : null
            // R2.1-09: mapToItem requires a QQuickItem target — root.window
            // is a QQuickWindow (type mismatch); the window CONTENT item is
            // the valid coordinate space for the backdrop source.
            sourceRect: Qt.rect(
                root.mapToItem(root.window ? root.window.contentItem : null, 0, 0).x,
                root.mapToItem(root.window ? root.window.contentItem : null, 0, 0).y,
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
            textureName: materialSpec.textureName
            textureOpacity: materialSpec.textureOpacity
            visible: root.textured && opacity > 0
        }

        // ── Specular glint: the brand cat silhouette (vector path from the
        // Michi brand artwork) as the light catch — a radial glow shaped
        // like the cat, not a circle ──
        Item {
            id: glintHost
            anchors.top: parent.top
            anchors.left: parent.left
            width: Math.min(parent.width, parent.height) * 0.55
            height: width * 0.584   // viewBox 100 x 58.4
            visible: parent.width > 0 && (
                root.glintMode === "michi" || root.glintMode === "always"
                || (root.glintMode === "auto" && root.raised))
            Shape {
                anchors.fill: parent
                ShapePath {
                    fillColor: "transparent"
                    strokeColor: "transparent"
                    fillGradient: RadialGradient {
                        centerX: 0.52
                        centerY: 0.45
                        centerRadius: 0.72
                        focalX: 0.52
                        focalY: 0.45
                        GradientStop { position: 0; color: MichiAccessibility.highContrast
                            ? MichiSemanticColors.glassGlintStrong : MichiSemanticColors.glassGlint }
                        GradientStop { position: 1; color: "transparent" }
                    }
                    PathSvg { path: "M78.013 0.298 C78.193 0.279 78.385 0.266 78.565 0.278 C79.052 0.308 79.500 0.573 79.819 0.932 C82.230 3.644 80.852 13.926 80.037 17.418 C79.874 18.119 79.677 18.812 79.447 19.494 C78.975 20.904 78.567 21.741 78.575 23.289 C78.557 25.131 79.414 26.792 79.875 28.537 C80.248 29.947 80.412 31.427 80.472 32.885 C80.511 33.830 80.421 34.768 80.370 35.712 C86.271 37.423 92.286 40.342 97.240 43.980 C98.161 44.656 99.178 45.449 100.000 46.237 C93.567 42.688 87.111 39.717 79.963 37.860 C79.308 39.984 79.036 40.714 77.835 42.650 C78.253 42.821 78.676 42.976 79.096 43.143 C83.232 44.788 87.211 46.966 90.734 49.694 C91.312 50.141 91.975 50.668 92.489 51.183 C91.532 50.581 90.256 49.958 89.243 49.418 C85.112 47.214 81.088 45.682 76.669 44.208 C75.363 45.845 73.487 47.373 71.803 48.590 C76.538 50.734 81.311 53.689 84.751 57.643 C80.285 54.329 75.388 51.641 70.195 49.651 C69.045 50.433 67.436 51.288 66.192 51.970 C62.736 53.867 59.287 55.647 55.495 56.766 C49.042 58.670 43.121 56.117 37.211 53.839 C34.226 52.689 32.304 52.063 29.474 50.508 C26.638 51.721 24.576 52.734 21.905 54.315 C20.700 55.043 19.516 55.805 18.354 56.600 C17.959 56.873 16.058 58.322 15.800 58.417 C15.922 58.194 17.074 57.023 17.274 56.828 C20.426 53.748 23.920 51.421 27.885 49.530 C25.828 48.133 24.623 47.052 23.027 45.137 C19.272 46.415 15.624 47.985 12.114 49.832 C10.623 50.613 9.245 51.428 7.779 52.231 C12.189 48.358 16.505 45.763 21.981 43.578 C21.058 41.898 20.546 40.548 20.327 38.621 C13.224 40.604 6.329 43.826 0.000 47.587 C5.929 42.261 12.678 38.730 20.258 36.354 C20.618 32.116 23.183 28.435 23.071 24.247 C22.995 21.414 21.590 18.242 20.927 15.441 C20.101 12.036 19.798 8.526 20.027 5.030 C20.094 4.100 20.138 3.012 20.649 2.203 C20.902 1.803 21.265 1.520 21.731 1.416 C24.174 0.873 30.228 5.487 32.177 6.964 C33.400 7.890 34.573 8.915 35.872 9.734 C36.952 10.416 38.244 10.998 39.541 11.037 C40.853 11.077 42.149 10.563 43.418 10.302 C45.367 9.901 47.440 9.549 49.431 9.444 C51.105 9.356 52.770 9.487 54.428 9.709 C57.546 10.128 61.454 11.280 64.448 9.979 C65.971 9.318 66.872 7.898 68.071 6.814 C70.332 4.767 72.912 3.015 75.542 1.482 C76.317 1.030 77.130 0.497 78.013 0.298 Z" }
                }
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
