import QtQuick
import "../theme"

// DEPRECATED: use MichiCard. This wrapper preserves the existing card API.
MichiCard {
    id: root
    objectName: "glassCard"
    controlObjectName: "glassCard"
    property string iconName: ""
    variant: "glass"
}
