import QtQuick
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
import QtQuick.Controls
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
import "../theme"

Item {
    id: root

<<<<<<< Updated upstream
    property real progress: 0
    property real from: 0
    property real to: 100
=======
<<<<<<< HEAD
    property real progress: 0.0
    property bool indeterminate: false
>>>>>>> Stashed changes
    property string statusText: ""
    property string title: ""
    property string cancelText: ""
    property bool showCancel: false
    property bool indeterminate: false
    property bool reducedMotion: false

    signal cancelRequested()

    objectName: "ProgressState"

    Accessible.role: Accessible.ProgressBar
    Accessible.name: title || "Progreso"
    Accessible.description: statusText + " " + Math.round((root.progress - root.from) / Math.max(1, root.to - root.from) * 100) + "%"

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.cardTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            visible: text !== ""
        }

        MichiProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            value: root.progress
            from: root.from
            to: root.to
            indeterminate: root.indeterminate
            reducedMotion: root.reducedMotion
            accessibleName: root.title || "Progreso"
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: {
                if (root.indeterminate) return root.statusText || "Procesando\u2026"
                var pct = Math.round((root.progress - root.from) / Math.max(1, root.to - root.from) * 100)
                return (root.statusText ? root.statusText + " \u2014 " : "") + pct + "%"
            }
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
<<<<<<< Updated upstream
            horizontalAlignment: Text.AlignHCenter
=======
            visible: !root.indeterminate
=======
    property real progress: 0
    property real from: 0
    property real to: 100
    property string statusText: ""
    property string title: ""
    property string cancelText: ""
    property bool showCancel: false
    property bool indeterminate: false
    property bool reducedMotion: false

    signal cancelRequested()

    objectName: "ProgressState"

    Accessible.role: Accessible.ProgressBar
    Accessible.name: title || "Progreso"
    Accessible.description: statusText + " " + Math.round((root.progress - root.from) / Math.max(1, root.to - root.from) * 100) + "%"

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.cardTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            visible: text !== ""
        }

        MichiProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            value: root.progress
            from: root.from
            to: root.to
            indeterminate: root.indeterminate
            reducedMotion: root.reducedMotion
            accessibleName: root.title || "Progreso"
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: {
                if (root.indeterminate) return root.statusText || "Procesando\u2026"
                var pct = Math.round((root.progress - root.from) / Math.max(1, root.to - root.from) * 100)
                return (root.statusText ? root.statusText + " \u2014 " : "") + pct + "%"
            }
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignHCenter
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }

        MichiButton {
            anchors.horizontalCenter: parent.horizontalCenter
<<<<<<< Updated upstream
            text: root.cancelText || "Cancelar"
            variant: "ghost"
            visible: root.showCancel
=======
<<<<<<< HEAD
            text: root.cancelText
            variant: "ghost"
            visible: root.cancelEnabled
=======
            text: root.cancelText || "Cancelar"
            variant: "ghost"
            visible: root.showCancel
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            onClicked: root.cancelRequested()
        }
    }
}
