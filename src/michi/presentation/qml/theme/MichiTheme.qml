pragma Singleton
import QtQuick

// Compatibility facade. New components consume focused token singletons;
// existing M6 views keep a stable API while M9 migrates incrementally.
QtObject {
    readonly property color backgroundBase: MichiSemanticColors.backplane
    readonly property color backgroundRaised: MichiPalette.graphite
    readonly property color surfacePrimary: MichiPalette.graphite
    readonly property color surfaceSecondary: MichiPalette.smoke
    readonly property color surfaceHover: MichiSemanticColors.surfaceHover
    readonly property color surfacePressed: MichiSemanticColors.surfacePressed
    readonly property color surfaceSelected: MichiSemanticColors.surfaceSelected
    readonly property color textPrimary: MichiPalette.textPrimary
    readonly property color textSecondary: MichiPalette.textSecondary
    readonly property color textMuted: MichiPalette.textMuted
    readonly property color textDisabled: MichiPalette.textDisabled
    readonly property color accent: MichiPalette.auroraBlue
    readonly property color accentHover: MichiSemanticColors.auroraHover
    readonly property color accentPressed: MichiSemanticColors.auroraPressed
    readonly property color borderSubtle: MichiSemanticColors.borderSubtle
    readonly property color borderStrong: MichiSemanticColors.borderStrong
    readonly property color success: MichiPalette.success
    readonly property color warning: MichiPalette.warning
    readonly property color error: MichiPalette.error

    readonly property int space2: MichiSpacing.xxs
    readonly property int space4: MichiSpacing.xs
    readonly property int space6: 6
    readonly property int space8: MichiSpacing.sm
    readonly property int space12: MichiSpacing.md
    readonly property int space16: MichiSpacing.lg
    readonly property int space20: 20
    readonly property int space24: MichiSpacing.xl
    readonly property int space32: MichiSpacing.xxl

    readonly property int radiusSmall: MichiRadius.xs
    readonly property int radiusMedium: MichiRadius.md
    readonly property int radiusLarge: MichiRadius.lg
    readonly property int radiusXLarge: MichiRadius.floating

    readonly property int fontSizeCaption: MichiTypography.caption
    readonly property int fontSizeBody: MichiTypography.secondary
    readonly property int fontSizeBodyLarge: MichiTypography.body
    readonly property int fontSizeTitle: MichiTypography.section
    readonly property int fontSizeHeading: MichiTypography.title
    readonly property string fontFamily: MichiTypography.family
    readonly property int fontWeightNormal: Font.Normal
    readonly property int fontWeightMedium: Font.Medium
    readonly property int fontWeightBold: Font.Bold

    readonly property int controlHeightSmall: MichiMetrics.controlSmall
    readonly property int controlHeightMedium: MichiMetrics.controlMedium
    readonly property int controlHeightLarge: MichiMetrics.controlLarge
    readonly property int iconSmall: MichiMetrics.iconSmall
    readonly property int iconMedium: MichiMetrics.iconMedium
    readonly property int iconLarge: MichiMetrics.iconLarge
    readonly property int durationFast: MichiMotion.micro
    readonly property int durationNormal: MichiMotion.standard
}
