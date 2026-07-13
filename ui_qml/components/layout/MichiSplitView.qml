import QtQuick
import "../../theme"
import "../foundations"

Item {
    id: root

    property real primaryRatio: 0.62
    property alias primaryContent: primaryHost.data
    property alias secondaryContent: secondaryHost.data
    readonly property bool compact: responsive.compact
    property int gap: MichiTheme.spacing.lg

    implicitHeight: compact
                    ? primaryHost.childrenRect.height + secondaryHost.childrenRect.height + gap
                    : Math.max(primaryHost.childrenRect.height, secondaryHost.childrenRect.height)

    MichiResponsive { id: responsive; availableWidth: root.width }

    Item {
        id: primaryHost
        width: root.compact ? parent.width : (parent.width - root.gap) * root.primaryRatio
        height: childrenRect.height
    }
    Item {
        id: secondaryHost
        x: root.compact ? 0 : primaryHost.width + root.gap
        y: root.compact ? primaryHost.height + root.gap : 0
        width: root.compact ? parent.width : parent.width - x
        height: childrenRect.height
    }
}
