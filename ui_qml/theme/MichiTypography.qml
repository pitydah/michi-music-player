pragma Singleton
import QtQuick

QtObject {
    property real scaleFactor: 1.0

    function scaled(baseSize: real): int {
        return Math.max(9, Math.round(baseSize * Math.max(0.85, Math.min(1.5, scaleFactor))))
    }

    readonly property int displaySize: scaled(32)
    readonly property int heroTitleSize: scaled(28)
    readonly property int pageTitleSize: scaled(22)
    readonly property int sectionTitleSize: scaled(20)
    readonly property int cardTitleSize: scaled(16)
    readonly property int bodySize: scaled(14)
    readonly property int secondarySize: scaled(13)
    readonly property int captionSize: scaled(12)
    readonly property int smallSize: scaled(12)
    readonly property int metaSize: scaled(11)
    readonly property int badgeSize: scaled(10)
    readonly property int buttonSize: scaled(14)
    readonly property int monospaceSize: scaled(13)

    readonly property real lineHeightTight: 1.16
    readonly property real lineHeightBody: 1.38
    readonly property real lineHeightRelaxed: 1.52

    readonly property int weightLight: 300
    readonly property int weightNormal: 400
    readonly property int weightMedium: 500
    readonly property int weightSemiBold: 600
    readonly property int weightBold: 700
}
