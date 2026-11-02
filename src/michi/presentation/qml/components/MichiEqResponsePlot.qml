import QtQuick
import "../primitives"
import "../theme"

// Calculated magnitude response from the canonical RBJ coefficients. This is
// not a spectrum, not a measurement and not an animation.
Item {
    id: root
    property var points: []
    property real sampleRate: 0
    implicitHeight: 112
    Accessible.role: Accessible.StaticText
    Accessible.name: qsTr("Calculated equalizer response, not a measurement")

    Canvas {
        id: canvas
        anchors.fill: parent
        visible: root.points.length > 1

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var padX = 8
            var padY = 8
            var minHz = root.points[0].hz
            var maxHz = root.points[root.points.length - 1].hz
            var logMin = Math.log(minHz)
            var logSpan = Math.log(maxHz) - logMin
            function xFor(hz) {
                return padX + (Math.log(hz) - logMin) / logSpan
                    * (width - 2 * padX)
            }
            function yFor(db) {
                var clamped = Math.max(-18, Math.min(18, db))
                return height / 2 - clamped / 18 * (height / 2 - padY)
            }

            ctx.strokeStyle = MichiSemanticColors.borderSubtle
            ctx.lineWidth = 1
            var marks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
            for (var i = 0; i < marks.length; ++i) {
                if (marks[i] < minHz || marks[i] > maxHz)
                    continue
                var x = xFor(marks[i])
                ctx.beginPath()
                ctx.moveTo(x, padY)
                ctx.lineTo(x, height - padY)
                ctx.stroke()
            }
            ctx.strokeStyle = MichiSemanticColors.borderStrong
            ctx.beginPath()
            ctx.moveTo(padX, height / 2)
            ctx.lineTo(width - padX, height / 2)
            ctx.stroke()

            ctx.strokeStyle = MichiPalette.auroraCyan
            ctx.lineWidth = 2
            ctx.beginPath()
            for (var p = 0; p < root.points.length; ++p) {
                var px = xFor(root.points[p].hz)
                var py = yFor(root.points[p].db)
                if (p === 0)
                    ctx.moveTo(px, py)
                else
                    ctx.lineTo(px, py)
            }
            ctx.stroke()
        }

        Connections {
            target: root
            function onPointsChanged() { canvas.requestPaint() }
            function onWidthChanged() { canvas.requestPaint() }
            function onHeightChanged() { canvas.requestPaint() }
        }
    }

    MichiText {
        anchors.centerIn: parent
        visible: root.points.length < 2
        text: qsTr("Select a track to calculate the response")
        role: "caption"
        color: MichiPalette.textMuted
    }

    MichiText {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        text: qsTr("Calculated response · not measured")
        role: "micro"
        color: MichiPalette.textMuted
    }
}
