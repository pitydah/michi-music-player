import QtQuick
import QtQuick.Effects
import "../theme"

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
    // Compatibility with the former IconSlot-backed MichiIcon registration.
    property alias iconName: root.iconKey
    property alias iconSource: root.source
    property alias iconSize: root.size
    property alias iconColor: root.color
    property bool rounded: false
    property string iconText: ""

    readonly property url resolvedSource: source.toString() !== ""
                                          ? source : iconSource(iconKey)

    function iconSource(key) {
        if (!key)
            return ""
        return "../../icons/sidebar/" + key + ".svg"
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
