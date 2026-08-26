pragma Singleton
import QtQuick

// MichiFormat — single source of truth for duration/file-size formatting.
// Replaces the 9 hand-rolled formatTime/formatDuration/formatFileSize copies.
// Locale-aware (W1): digits come from Qt.locale() (native digits in
// arabic-style locales) and unit words are translatable via qsTr.
QtObject {
    function _digit(n) {
        // Locale-aware digits (western, arabic-indic, etc.). n MUST be a
        // number: Qt.locale().toString(string) tries QDateTime conversion
        // ("Could not convert argument 0 from 01 to QDateTime"). Zero-
        // padding is done numerically by the callers before formatting.
        return Qt.locale().toString(n)
    }

    function _pad2(n) {
        // numeric zero-padding (10 -> "10", 5 -> "05") — never a string
        // fed to the locale formatter
        return n < 10 ? "0" + n : "" + n
    }

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
            return _digit(hours) + ":" + _pad2(minutes)
                + ":" + _pad2(seconds)
        return _digit(minutes) + ":" + _pad2(seconds)
    }

    // "N hr N min" / "N min" (album-level durations). Units translatable.
    function formatHoursMinutes(milliseconds) {
        var seconds = Math.max(0, Math.floor(milliseconds / 1000))
        var minutes = Math.floor(seconds / 60)
        var hours = Math.floor(minutes / 60)
        var remainingMinutes = minutes % 60
        if (hours > 0)
            return _digit(hours) + " " + qsTr("hr") + " "
                + _digit(remainingMinutes) + " " + qsTr("min")
        return _digit(minutes) + " " + qsTr("min")
    }

    // "N.N MB" / "N.NN GB", "Unknown" for missing input.
    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0)
            return qsTr("Unknown")
        if (bytes >= 1073741824)
            return Qt.locale().toString(bytes / 1073741824, "f", 2) + " GB"
        return Qt.locale().toString(bytes / 1048576, "f", 1) + " MB"
    }
}
