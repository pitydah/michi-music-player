import QtQuick
import QtQuick.Effects
import "../theme"

/* MichiIcon — canonical icon component using Fluent System Icons.
 *
 * Resolution order:
 *   1. Explicit source URL (if set)
 *   2. Fluent icon: ../assets/icons/fluent/{variant}/{key}.svg
 *   3. Legacy fallback: ../../icons/sidebar/{key}.svg
 *
 * Variant selection:
 *   active=true  → "filled" variant
 *   active=false → "regular" variant
 */

Item {
    id: root
    objectName: controlObjectName

    property string controlObjectName: "michiIcon"
    property url source: ""
    property string iconKey: ""
    property int size: 24
    property color color: active ? MichiTheme.colors.accentPrimary
                                 : MichiTheme.colors.textSecondary
    property bool active: false
    property bool disabled: false
    property string accessibleName: ""
    property alias iconName: root.iconKey
    property alias iconSource: root.source
    property alias iconSize: root.size
    property alias iconColor: root.color
    property bool rounded: false
    property string iconText: ""

    readonly property string _variant: root.active ? "filled" : "regular"

    readonly property url resolvedSource: {
        if (source.toString() !== "")
            return source
        var key = iconKey
        if (!key) return ""

        // Try Fluent icon first
        var fluentPath = "../assets/icons/fluent/" + root._variant + "/" + key + ".svg"
        if (typeof fluentIconExists !== "undefined" && fluentIconExists(key))
            return fluentPath

        // Fallback to legacy icon
        return "../../icons/sidebar/" + key + ".svg"
    }

    readonly property var _fluentCache: ({
        "ai": true, "albums": true, "artists": true,
        "capture": true, "devices": true, "folders": true,
        "history": true, "home": true, "home_audio": true,
        "library": true, "connections": true, "mix": true,
        "outputs": true, "playlists": true, "queue": true,
        "radio": true, "search": true, "settings": true,
        "songs": true, "streaming": true, "sync": true,
    })

    function fluentIconExists(key) {
        return _fluentCache.hasOwnProperty(key)
    }

    implicitWidth: size
    implicitHeight: size
    opacity: disabled ? MichiTheme.disabledOpacity : 1.0
    Accessible.role: Accessible.Graphic
    Accessible.name: accessibleName

    Image {
        id: image
        anchors.centerIn: parent
        width: root.size
        height: root.size
        source: root.resolvedSource
        sourceSize.width: root.size
        sourceSize.height: root.size
        fillMode: Image.PreserveAspectFit
        visible: false
    }

    MultiEffect {
        anchors.fill: image
        source: image
        colorization: 1.0
        colorizationColor: root.color
    }
}
