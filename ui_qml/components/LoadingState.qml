import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
import "../theme"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
import "../theme"
import "foundations"
=======
import QtQuick.Controls as QQC2
import "../theme"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

Item {
    id: root

    property string title: "Cargando"
    property string message: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property bool busy: true
    property bool reducedMotion: false

    objectName: "LoadingState"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string objectName: "loadingState"
    property bool reducedMotion: MichiReducedMotion.enabled
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightMedium
            horizontalAlignment: Text.AlignHCenter
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            wrapMode: Text.WordWrap
=======
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            width: Math.min(Math.max(implicitWidth, 240), 460)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
            width: Math.min(Math.max(implicitWidth, 240), 460)
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes

        MichiProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 160
            indeterminate: true
            visible: root.busy
            reducedMotion: root.reducedMotion
            accessibleName: root.title
        }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    }
}
