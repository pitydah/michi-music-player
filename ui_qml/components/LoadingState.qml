import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Loading State"
    objectName: "loadingState"
    focus: true
    id: root

    property string title: "Cargando"
    property string message: ""
    property bool busy: true
    property bool reducedMotion: false

    objectName: "LoadingState"

    Accessible.role: Accessible.Indicator
    Accessible.name: title
    Accessible.description: message || "Cargando contenido"

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        QQC2.BusyIndicator {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 32
            height: 32
            running: root.busy
            Accessible.role: Accessible.Indicator
            Accessible.name: root.title

            contentItem: Item {
                Rectangle {
                    id: spinner
                    width: parent.width * 0.75
                    height: width
                    radius: width / 2
                    anchors.centerIn: parent
                    color: "transparent"
                    border.width: 3
                    border.color: MichiTheme.colors.accentBlue

                    SequentialAnimation on rotation {
                        running: root.busy && !root.reducedMotion
                        loops: Animation.Infinite
                        PropertyAnimation { from: 0; to: 360; duration: 800 }
                    }
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightMedium
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        MichiProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 160
            indeterminate: true
            visible: root.busy
            reducedMotion: root.reducedMotion
            accessibleName: root.title
        }
    }
}
