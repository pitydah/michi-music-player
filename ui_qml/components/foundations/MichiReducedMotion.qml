import QtQuick
import "../../theme"

QtObject {
    id: root

    property bool enabled: false

    function duration(normalDuration) {
        return enabled ? Math.min(normalDuration, MichiTheme.motion.reduced) : normalDuration
    }

    function optionalDuration(normalDuration) {
        return enabled ? 0 : normalDuration
    }
}
