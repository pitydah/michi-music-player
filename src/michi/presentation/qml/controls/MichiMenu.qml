import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Menu {
    id: root

    // One geometry authority for the whole Michi menu family.
    property real minimumMenuWidth: 260
    property real maximumMenuWidth: 420

    topPadding: MichiSpacing.xs
    bottomPadding: MichiSpacing.xs
    leftPadding: MichiSpacing.xs
    rightPadding: MichiSpacing.xs

    // Popup implicit sizing must be derived from deterministic content or
    // background dimensions. Never allow a separator to become the only
    // meaningful width authority.
    implicitWidth: Math.max(
        root.minimumMenuWidth,
        Math.min(
            root.maximumMenuWidth,
            Math.max(
                root.implicitBackgroundWidth + root.leftInset + root.rightInset,
                root.implicitContentWidth + root.leftPadding + root.rightPadding
            )
        )
    )

    implicitHeight: Math.max(
        root.implicitBackgroundHeight + root.topInset + root.bottomInset,
        root.implicitContentHeight + root.topPadding + root.bottomPadding
    )

    // IMPORTANT: do not animate x/y. They are popup-placement coordinates.
    enter: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: MichiAccessibility.reducedMotion
                    ? 0 : MichiMotion.popupOpen
                easing.type: MichiMotion.outCubic
            }
            NumberAnimation {
                property: "scale"
                from: 0.985
                to: 1
                duration: MichiAccessibility.reducedMotion
                    ? 0 : MichiMotion.popupOpen
                easing.type: MichiMotion.outCubic
            }
        }
    }

    exit: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: MichiAccessibility.reducedMotion
                    ? 0 : MichiMotion.popupClose
                easing.type: MichiMotion.outCubic
            }
            NumberAnimation {
                property: "scale"
                from: 1
                to: 0.985
                duration: MichiAccessibility.reducedMotion
                    ? 0 : MichiMotion.popupClose
                easing.type: MichiMotion.outCubic
            }
        }
    }

    // This delegate styles Action-backed items and the proxy item created by
    // Qt for a nested Menu. Its read-only subMenu property drives the arrow.
    delegate: MichiMenuItem { }

    background: MichiGlassSurface {
        implicitWidth: root.minimumMenuWidth
        implicitHeight: MichiMetrics.controlMedium
        elevation: "elevated"
        materialRole: MichiMaterialRole.elevated
        contentPadding: 0
        radius: MichiRadius.md
        tileSeed: 9
        shadowed: true
        textured: true
        glintMode: "edge"
    }
}
