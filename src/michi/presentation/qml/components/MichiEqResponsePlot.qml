import QtQuick
import "../primitives"
import "../theme"

// Calculated magnitude response from the canonical RBJ coefficients. This is
// not a spectrum, not a measurement and not an animation.
Item {
    id: root
    property var points: []
    property real sampleRate: 0
    implicitHeight: 220
    Accessible.role: Accessible.StaticText
    Accessible.name: qsTr("Calculated equalizer response, not a measurement")

    Canvas {
        id: canvas
        anchors.fill: parent
        visible: root.points.length > 1

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var padLeft = 40
            var padRight = 16
            var padTop = 16
            var padBottom = 26
            var minHz = root.points[0].hz
            var maxHz = root.points[root.points.length - 1].hz
            var logMin = Math.log(minHz)
            var logSpan = Math.log(maxHz) - logMin
            function xFor(hz) {
                return padLeft + (Math.log(hz) - logMin) / logSpan
                    * (width - padLeft - padRight)
            }
            function yFor(db) {
                var clamped = Math.max(-18, Math.min(18, db))
                var mid = padTop + (height - padTop - padBottom) / 2
                return mid - clamped / 18 * ((height - padTop - padBottom) / 2)
            }

            ctx.strokeStyle = MichiSemanticColors.borderSubtle
            ctx.lineWidth = 1
            var marks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
            for (var i = 0; i < marks.length; ++i) {
                if (marks[i] < minHz || marks[i] > maxHz)
                    continue
                var x = xFor(marks[i])
                ctx.beginPath()
                ctx.moveTo(x, padTop)
                ctx.lineTo(x, height - padBottom)
                ctx.stroke()
            }

            ctx.fillStyle = MichiPalette.textMuted
            ctx.font = "10px sans-serif"
            ctx.textAlign = "right"
            ctx.textBaseline = "middle"
            var levels = [12, 0, -12]
            for (var level = 0; level < levels.length; ++level) {
                var levelY = yFor(levels[level])
                ctx.strokeStyle = levels[level] === 0
                    ? MichiSemanticColors.borderStrong
                    : MichiSemanticColors.borderSubtle
                ctx.beginPath()
                ctx.moveTo(padLeft, levelY)
                ctx.lineTo(width - padRight, levelY)
                ctx.stroke()
                ctx.fillText((levels[level] > 0 ? "+" : "")
                    + levels[level] + " dB", padLeft - 6, levelY)
            }

            ctx.textAlign = "center"
            ctx.textBaseline = "top"
            var labels = [[20, "20"], [1000, "1k"], [20000, "20k"]]
            for (var label = 0; label < labels.length; ++label) {
                if (labels[label][0] < minHz || labels[label][0] > maxHz)
                    continue
                ctx.fillText(labels[label][1] + " Hz",
                    xFor(labels[label][0]), height - padBottom + 6)
            }

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

            ctx.fillStyle = MichiPalette.textSecondary
            ctx.textAlign = "right"
            ctx.textBaseline = "top"
            ctx.fillText(qsTr("Calculated response · draft"),
                width - padRight, padTop + 2)
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

}
