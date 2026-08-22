pragma Singleton
import QtQuick

// MichiFormat — single source of truth for duration/file-size formatting.
// Replaces the 9 hand-rolled formatTime/formatDuration/formatFileSize copies
// so format rules (and future QLocale support) live in one place.
QtObject {
    // m:ss for <1h, h:mm:ss for ≥1h. Empty string for non-positive input.
    // floor (not round): durations never display more than they really are.
    function formatDuration(ms) {
        if (!ms || ms <= 0)
            return ""
        var totalSeconds = Math.floor(ms / 1000)
        var hours = Math.floor(totalSeconds / 3600)
        var minutes = Math.floor((totalSeconds % 3600) / 60)
        var seconds = totalSeconds % 60
        if (hours > 0)
            return hours + ":" + (minutes < 10 ? "0" : "") + minutes
                + ":" + (seconds < 10 ? "0" : "") + seconds
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    // "N hr N min" / "N min" (album-level durations).
    function formatHoursMinutes(milliseconds) {
        var seconds = Math.max(0, Math.floor(milliseconds / 1000))
        var minutes = Math.floor(seconds / 60)
        var hours = Math.floor(minutes / 60)
        var remainingMinutes = minutes % 60
        if (hours > 0)
            return hours + " hr " + remainingMinutes + " min"
        return minutes + " min"
    }

    // "N.N MB" / "N.NN GB", "Unknown" for missing input.
    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0)
            return "Unknown"
        if (bytes >= 1073741824)
            return (bytes / 1073741824).toFixed(2) + " GB"
        return (bytes / 1048576).toFixed(1) + " MB"
    }
}
