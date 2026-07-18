import QtQuick
import "../theme"
import "../materials"

GlassMaterial {
    id: root

    property int skeletonCardCount: 3
    property int skeletonCardHeight: 120

    width: parent ? parent.width : 300
    radius: MichiTheme.radius.md

    Column {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.md

        Repeater {
            model: root.skeletonCardCount

            Row {
                spacing: MichiTheme.spacing.md
                width: parent.width

                Skeleton {
                    skeletonWidth: 48
                    skeletonHeight: 48
                    skeletonRadius: MichiTheme.radius.sm
                }

                Column {
                    spacing: MichiTheme.spacing.xs
                    anchors.verticalCenter: parent.verticalCenter

                    Skeleton { skeletonWidth: parent.parent ? parent.parent.width * 0.4 : 120; skeletonHeight: 14 }
                    Skeleton { skeletonWidth: parent.parent ? parent.parent.width * 0.25 : 80; skeletonHeight: 12 }
                }
            }
        }
    }
}
