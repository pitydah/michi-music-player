pragma Singleton
import QtQuick

QtObject {
    readonly property int instant: MichiAccessibility.reducedMotion ? 0 : 80
    readonly property int micro: MichiAccessibility.reducedMotion ? 0 : 110
    readonly property int standard: MichiAccessibility.reducedMotion ? 0 : 180
    readonly property int panel: MichiAccessibility.reducedMotion ? 0 : 220
    readonly property int page: MichiAccessibility.reducedMotion ? 0 : 240
    readonly property int artwork: MichiAccessibility.reducedMotion ? 0 : 210
    readonly property int selection: MichiAccessibility.reducedMotion ? 0 : 160
    readonly property int viewTransition: MichiAccessibility.reducedMotion ? 0 : 200
    readonly property int popupOpen: MichiAccessibility.reducedMotion ? 0 : 200
    readonly property int popupClose: MichiAccessibility.reducedMotion ? 0 : 140
    readonly property int viewExit: MichiAccessibility.reducedMotion ? 0 : 170
    readonly property int viewEnter: MichiAccessibility.reducedMotion ? 0 : 260
    readonly property int paletteCrossfade: MichiAccessibility.reducedMotion ? 0 : 300
    readonly property int vinylReveal: MichiAccessibility.reducedMotion ? 0 : 240
    readonly property int outCubic: Easing.OutCubic
    readonly property int outQuart: Easing.OutQuart
    readonly property int inOutCubic: Easing.InOutCubic
}
