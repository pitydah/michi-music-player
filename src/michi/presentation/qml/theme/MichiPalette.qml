pragma Singleton
import QtQuick

QtObject {
    readonly property color obsidian: "#090B11"
    readonly property color obsidianDeep: "#07090E"
    readonly property color obsidianRaised: "#0D111B"
    readonly property color graphite: "#14171C"
    readonly property color playerSurfaceTop: "#0B0E16"
    readonly property color trackSurfaceTop: "#141824"
    readonly property color trackSurfaceHover: "#171B29"
    readonly property color trackSurfaceBottom: "#0D1018"
    readonly property color smoke: "#1F232A"
    readonly property color smokeRaised: "#282D36"
    // Playlist editorial hero — deep, low-saturation blue atmosphere
    readonly property color playlistHeroTop: "#152A45"
    readonly property color playlistHeroMid: "#13243D"
    readonly property color playlistHeroBottom: "#0A0D14"
    readonly property color textPrimary: "#ECEEF3"
    // High-contrast mode lifts the secondary tiers so all functional text
    // exceeds 7:1 on obsidian (borders/opacity alone are not enough).
    readonly property color textSecondary: MichiAccessibility.highContrast ? "#C9CEDB" : "#9CA1AE"
    readonly property color textMuted: MichiAccessibility.highContrast ? "#ADB3C2" : "#8A90A0" // WCAG AA >=4.5:1 on obsidian/graphite/smoke
    readonly property color textDisabled: MichiAccessibility.highContrast ? "#8A91A1" : "#4C515D"
    readonly property color auroraBlue: "#4CA6FF"
    readonly property color auroraCyan: "#21D6E6"
    readonly property color auroraPurple: "#9A7CFF"
    readonly property color auroraGreen: "#5DE3A2"
    readonly property color success: "#5DE3A2"
    readonly property color warning: "#E4B866"
    readonly property color error: "#FF6B7A"
}
