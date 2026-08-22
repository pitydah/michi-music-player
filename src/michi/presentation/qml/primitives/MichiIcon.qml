import QtQuick
import "../theme"

Item {
    id: root
    property string name: "circle"
    property color iconColor: MichiPalette.textSecondary
    property real strokeWidth: 1.7
    implicitWidth: MichiMetrics.iconMedium
    implicitHeight: MichiMetrics.iconMedium
    Accessible.role: Accessible.Graphic
    Accessible.name: name

    onNameChanged: canvas.requestPaint()
    onIconColorChanged: canvas.requestPaint()
    onStrokeWidthChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        function line(ctx, x1, y1, x2, y2) {
            ctx.moveTo(x1, y1)
            ctx.lineTo(x2, y2)
        }

        onPaint: {
            var ctx = getContext("2d")
            var w = width
            var h = height
            ctx.reset()
            if (w <= 0 || h <= 0) return

            ctx.save()
            ctx.scale(w / 24.0, h / 24.0)

            ctx.strokeStyle = root.iconColor
            ctx.fillStyle = root.iconColor
            ctx.lineWidth = root.strokeWidth
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.beginPath()

            if (root.name === "play") {
                ctx.moveTo(8, 5.5)
                ctx.lineTo(18.5, 12)
                ctx.lineTo(8, 18.5)
                ctx.closePath()
                ctx.fill()
                ctx.restore()
                return
            } else if (root.name === "pause") {
                ctx.fillRect(6, 5, 3.6, 14)
                ctx.fillRect(14.4, 5, 3.6, 14)
                ctx.restore()
                return
            } else if (root.name === "stop") {
                ctx.fillRect(6, 6, 12, 12)
                ctx.restore()
                return
            } else if (root.name === "previous") {
                ctx.fillRect(4.5, 5.5, 2.2, 13)
                ctx.moveTo(18.5, 5.5)
                ctx.lineTo(8.5, 12)
                ctx.lineTo(18.5, 18.5)
                ctx.closePath()
                ctx.fill()
                ctx.restore()
                return
            } else if (root.name === "next") {
                ctx.fillRect(17.3, 5.5, 2.2, 13)
                ctx.moveTo(5.5, 5.5)
                ctx.lineTo(15.5, 12)
                ctx.lineTo(5.5, 18.5)
                ctx.closePath()
                ctx.fill()
                ctx.restore()
                return
            } else if (root.name === "back") {
                line(ctx, 18, 12, 6, 12)
                line(ctx, 11, 6.5, 6, 12)
                line(ctx, 11, 17.5, 6, 12)
            } else if (root.name === "output-status" || root.name === "volume" || root.name === "mute") {
                // High-End Acoustic Transducer / Volume Horn
                ctx.moveTo(4, 9.5)
                ctx.lineTo(7.5, 9.5)
                ctx.lineTo(12, 5.5)
                ctx.lineTo(12, 18.5)
                ctx.lineTo(7.5, 14.5)
                ctx.lineTo(4, 14.5)
                ctx.closePath()
                if (root.name === "mute") {
                    line(ctx, 15, 9, 20, 15)
                    line(ctx, 20, 9, 15, 15)
                } else {
                    ctx.moveTo(15, 9)
                    ctx.arc(12, 12, 4.5, -0.7, 0.7)
                    ctx.moveTo(18, 6.5)
                    ctx.arc(12, 12, 8, -0.75, 0.75)
                }
            } else if (root.name === "search") {
                ctx.arc(10.5, 10.5, 5.5, 0, Math.PI * 2)
                line(ctx, 14.5, 14.5, 19.5, 19.5)
            } else if (root.name === "library") {
                // Audiophile vinyl sleeve with sliding record
                ctx.rect(4, 4, 11, 16)
                ctx.moveTo(17, 6.5)
                ctx.arc(14.5, 12, 5.5, -0.92, 0.92)
                ctx.moveTo(15.7, 12)
                ctx.arc(14.5, 12, 1.2, 0, Math.PI * 2)
            } else if (root.name === "track") {
                // Beamed eighth note pair with clean optical symmetry
                line(ctx, 8.5, 6, 8.5, 16)
                line(ctx, 8.5, 6, 18, 4)
                line(ctx, 18, 4, 18, 14)
                line(ctx, 8.5, 8.5, 18, 6.5)
                ctx.moveTo(8.5, 16)
                ctx.arc(6, 16, 2.5, 0, Math.PI * 2)
                ctx.moveTo(18, 14)
                ctx.arc(15.5, 14, 2.5, 0, Math.PI * 2)
            } else if (root.name === "album") {
                // Balanced album sleeve (15x15) with concentric vinyl grooves
                ctx.rect(4.5, 4.5, 15, 15)
                ctx.moveTo(16, 12)
                ctx.arc(12, 12, 4, 0, Math.PI * 2)
                ctx.moveTo(13.5, 12)
                ctx.arc(12, 12, 1.5, 0, Math.PI * 2)
            } else if (root.name === "history") {
                // Precision clock with circular return arrow
                ctx.arc(12, 12, 7.5, -0.3, Math.PI * 1.6)
                line(ctx, 12, 12, 12, 8)
                line(ctx, 12, 12, 15.5, 12)
                line(ctx, 5.5, 4.5, 5.5, 9)
                line(ctx, 5.5, 4.5, 10, 4.5)
            } else if (root.name === "recent") {
                // Precision clock with distinct plus badge
                ctx.arc(10.5, 12, 6.5, 0, Math.PI * 2)
                line(ctx, 10.5, 12, 10.5, 8.5)
                line(ctx, 10.5, 12, 13.5, 12)
                line(ctx, 19, 6.5, 19, 11.5)
                line(ctx, 16.5, 9, 21.5, 9)
            } else if (root.name === "playlist") {
                line(ctx, 4, 6.5, 14, 6.5)
                line(ctx, 4, 11.5, 14, 11.5)
                line(ctx, 4, 16.5, 11, 16.5)
                line(ctx, 16.5, 7.5, 16.5, 16.5)
                line(ctx, 16.5, 7.5, 20, 6.5)
                ctx.moveTo(16.5, 16.5)
                ctx.arc(14.5, 16.5, 2, 0, Math.PI * 2)
            } else if (root.name === "plus" || root.name === "add") {
                line(ctx, 12, 5, 12, 19)
                line(ctx, 5, 12, 19, 12)
            } else if (root.name === "pin") {
                line(ctx, 8, 4.5, 16, 4.5)
                line(ctx, 9.5, 4.5, 9.5, 12)
                line(ctx, 14.5, 4.5, 14.5, 12)
                line(ctx, 6.5, 12, 17.5, 12)
                line(ctx, 12, 12, 12, 19.5)
            } else if (root.name === "cat") {
                // Minimalist Japanese feline crest / modernist geometric emblem
                ctx.moveTo(4.5, 9)
                ctx.lineTo(6, 4.5)
                ctx.lineTo(9.5, 7.5)
                ctx.lineTo(14.5, 7.5)
                ctx.lineTo(18, 4.5)
                ctx.lineTo(19.5, 9)
                ctx.lineTo(18.5, 15)
                ctx.lineTo(12, 19.5)
                ctx.lineTo(5.5, 15)
                ctx.closePath()
                // Inner precision eye markers
                line(ctx, 8, 12, 10, 12)
                line(ctx, 14, 12, 16, 12)
                line(ctx, 12, 14, 12, 15.5)
            } else if (root.name === "view-grid") {
                ctx.rect(4.5, 4.5, 6, 6)
                ctx.rect(13.5, 4.5, 6, 6)
                ctx.rect(4.5, 13.5, 6, 6)
                ctx.rect(13.5, 13.5, 6, 6)
            } else if (root.name === "view-path") {
                ctx.rect(8, 4.5, 8, 15)
                ctx.rect(3.5, 7, 3, 10)
                ctx.rect(17.5, 7, 3, 10)
            } else if (root.name === "view-vinyl") {
                ctx.rect(3.5, 4.5, 11, 15)
                ctx.moveTo(17, 6.5)
                ctx.arc(14.5, 12, 6.5, -0.95, 0.95)
                ctx.moveTo(15.5, 12)
                ctx.arc(14.5, 12, 1, 0, Math.PI * 2)
            } else if (root.name === "view-timeline") {
                line(ctx, 7, 3.5, 7, 20.5)
                ctx.moveTo(8.5, 6.5)
                ctx.arc(7, 6.5, 1.5, 0, Math.PI * 2)
                ctx.moveTo(8.5, 12)
                ctx.arc(7, 12, 1.5, 0, Math.PI * 2)
                ctx.moveTo(8.5, 17.5)
                ctx.arc(7, 17.5, 1.5, 0, Math.PI * 2)
                line(ctx, 10.5, 6.5, 19.5, 6.5)
                line(ctx, 10.5, 12, 17.5, 12)
                line(ctx, 10.5, 17.5, 19, 17.5)
            } else if (root.name === "view-magazine") {
                ctx.rect(4, 4.5, 9.5, 15)
                ctx.rect(15, 4.5, 5, 5)
                line(ctx, 15, 12.5, 20, 12.5)
                line(ctx, 15, 15.5, 20, 15.5)
                line(ctx, 15, 18.5, 18.5, 18.5)
            } else if (root.name === "view-list") {
                ctx.rect(4.5, 5, 3, 3)
                ctx.rect(4.5, 10.5, 3, 3)
                ctx.rect(4.5, 16, 3, 3)
                line(ctx, 9.5, 6.5, 19.5, 6.5)
                line(ctx, 9.5, 12, 19.5, 12)
                line(ctx, 9.5, 17.5, 19.5, 17.5)
            } else if (root.name === "density-comfortable") {
                line(ctx, 5, 7, 19, 7)
                line(ctx, 5, 17, 19, 17)
            } else if (root.name === "density-standard") {
                line(ctx, 5, 6, 19, 6)
                line(ctx, 5, 12, 19, 12)
                line(ctx, 5, 18, 18, 18)
            } else if (root.name === "density-compact") {
                line(ctx, 5, 5, 19, 5)
                line(ctx, 5, 9.5, 19, 9.5)
                line(ctx, 5, 14.5, 19, 14.5)
                line(ctx, 5, 19, 19, 19)
            } else if (root.name === "queue") {
                // Precision play queue with tier lines and play indicator
                line(ctx, 4, 6.5, 20, 6.5)
                line(ctx, 4, 11.5, 13, 11.5)
                line(ctx, 4, 16.5, 11, 16.5)
                ctx.moveTo(15.5, 11.5)
                ctx.lineTo(20.5, 14.5)
                ctx.lineTo(15.5, 17.5)
                ctx.closePath()
            } else if (root.name === "shuffle") {
                ctx.moveTo(4, 7)
                ctx.lineTo(7.5, 7)
                ctx.bezierCurveTo(11, 7, 13, 17, 16.5, 17)
                line(ctx, 16.5, 17, 20, 17)
                line(ctx, 17.5, 14.5, 20, 17)
                line(ctx, 17.5, 19.5, 20, 17)

                ctx.moveTo(4, 17)
                ctx.lineTo(7.5, 17)
                ctx.bezierCurveTo(11, 17, 13, 7, 16.5, 7)
                line(ctx, 16.5, 7, 20, 7)
                line(ctx, 17.5, 4.5, 20, 7)
                line(ctx, 17.5, 9.5, 20, 7)
            } else if (root.name === "repeat" || root.name === "repeat-one") {
                ctx.moveTo(4.5, 8.5)
                ctx.lineTo(17.5, 8.5)
                line(ctx, 15, 6, 17.5, 8.5)
                line(ctx, 15, 11, 17.5, 8.5)
                ctx.moveTo(19.5, 15.5)
                ctx.lineTo(6.5, 15.5)
                line(ctx, 9, 13, 6.5, 15.5)
                line(ctx, 9, 18, 6.5, 15.5)
                if (root.name === "repeat-one") {
                    ctx.stroke()
                    ctx.beginPath()
                    ctx.font = "bold 8px sans-serif"
                    ctx.textAlign = "center"
                    ctx.textBaseline = "middle"
                    ctx.fillText("1", 12, 12)
                    ctx.restore()
                    return
                }
            } else if (root.name === "sliders" || root.name === "equalizer") {
                if (root.name === "equalizer") {
                    // Audiophile 4-band precision spectrum bars
                    line(ctx, 5.5, 19, 5.5, 11)
                    line(ctx, 9.5, 19, 9.5, 6)
                    line(ctx, 14.5, 19, 14.5, 13)
                    line(ctx, 18.5, 19, 18.5, 8)
                    // Precision baseline
                    line(ctx, 3.5, 20, 20.5, 20)
                } else {
                    line(ctx, 6, 4, 6, 20)
                    line(ctx, 12, 4, 12, 20)
                    line(ctx, 18, 4, 18, 20)
                    line(ctx, 3.5, 8, 8.5, 8)
                    line(ctx, 9.5, 16, 14.5, 16)
                    line(ctx, 15.5, 11, 20.5, 11)
                }
            } else if (root.name === "sort") {
                line(ctx, 4.5, 6.5, 15.5, 6.5)
                line(ctx, 4.5, 12, 12.5, 12)
                line(ctx, 4.5, 17.5, 9.5, 17.5)
                line(ctx, 17.5, 5.5, 17.5, 18.5)
                line(ctx, 15, 16, 17.5, 18.5)
                line(ctx, 20, 16, 17.5, 18.5)
            } else if (root.name === "sort-ascending") {
                line(ctx, 12, 18.5, 12, 5.5)
                line(ctx, 8.5, 9, 12, 5.5)
                line(ctx, 15.5, 9, 12, 5.5)
            } else if (root.name === "sort-descending") {
                line(ctx, 12, 5.5, 12, 18.5)
                line(ctx, 8.5, 15, 12, 18.5)
                line(ctx, 15.5, 15, 12, 18.5)
            } else if (root.name === "filter") {
                ctx.moveTo(4, 5.5)
                ctx.lineTo(20, 5.5)
                ctx.lineTo(14, 12.5)
                ctx.lineTo(14, 18)
                ctx.lineTo(10, 19.5)
                ctx.lineTo(10, 12.5)
                ctx.closePath()
            } else if (root.name === "audio-output") {
                // Studio Reference Monitor Speaker
                ctx.rect(5, 3.5, 14, 17)
                ctx.moveTo(14, 7.5)
                ctx.arc(12, 7.5, 2, 0, Math.PI * 2)
                ctx.moveTo(16, 14.5)
                ctx.arc(12, 14.5, 4, 0, Math.PI * 2)
                ctx.moveTo(13.2, 14.5)
                ctx.arc(12, 14.5, 1.2, 0, Math.PI * 2)
            } else if (root.name === "audio-engine") {
                // Discrete DAC microchip with pure sinusoidal waveform
                ctx.rect(5.5, 5.5, 13, 13)
                line(ctx, 8.5, 3.5, 8.5, 5.5)
                line(ctx, 15.5, 3.5, 15.5, 5.5)
                line(ctx, 8.5, 18.5, 8.5, 20.5)
                line(ctx, 15.5, 18.5, 15.5, 20.5)
                line(ctx, 3.5, 8.5, 5.5, 8.5)
                line(ctx, 3.5, 15.5, 5.5, 15.5)
                line(ctx, 18.5, 8.5, 20.5, 8.5)
                line(ctx, 18.5, 15.5, 20.5, 15.5)
                ctx.moveTo(8, 12)
                ctx.bezierCurveTo(9.5, 9, 10.5, 15, 12, 12)
                ctx.bezierCurveTo(13.5, 9, 14.5, 15, 16, 12)
            } else if (root.name === "device") {
                ctx.rect(5, 4, 14, 16)
                line(ctx, 8, 7.5, 16, 7.5)
                ctx.moveTo(14.5, 13)
                ctx.arc(12, 13, 2.5, 0, Math.PI * 2)
                ctx.moveTo(13, 17)
                ctx.arc(12, 17, 1, 0, Math.PI * 2)
            } else if (root.name === "settings") {
                // Precision knurled rotary dial with central axis hub
                ctx.arc(12, 12, 4, 0, Math.PI * 2)
                for (var i = 0; i < 8; i++) {
                    var angle = i * Math.PI / 4.0
                    var cosA = Math.cos(angle)
                    var sinA = Math.sin(angle)
                    ctx.moveTo(12 + cosA * 5.5, 12 + sinA * 5.5)
                    ctx.lineTo(12 + cosA * 8.5, 12 + sinA * 8.5)
                }
            } else if (root.name === "heart") {
                // Symmetrical, optically balanced heart
                ctx.moveTo(12, 19.5)
                ctx.bezierCurveTo(4.5, 14, 3.5, 7.5, 8, 5.5)
                ctx.bezierCurveTo(10.5, 4.5, 12, 6.8, 12, 8)
                ctx.bezierCurveTo(12, 6.8, 13.5, 4.5, 16, 5.5)
                ctx.bezierCurveTo(20.5, 7.5, 19.5, 14, 12, 19.5)
            } else if (root.name === "close") {
                line(ctx, 6, 6, 18, 18)
                line(ctx, 18, 6, 6, 18)
            } else if (root.name === "zoom-out") {
                ctx.arc(10.5, 10.5, 5.5, 0, Math.PI * 2)
                line(ctx, 14.5, 14.5, 19.5, 19.5)
                line(ctx, 7.5, 10.5, 13.5, 10.5)
            } else if (root.name === "zoom-in") {
                ctx.arc(10.5, 10.5, 5.5, 0, Math.PI * 2)
                line(ctx, 14.5, 14.5, 19.5, 19.5)
                line(ctx, 7.5, 10.5, 13.5, 10.5)
                line(ctx, 10.5, 7.5, 10.5, 13.5)
            } else if (root.name === "chevron-left") {
                line(ctx, 15, 6, 9, 12)
                line(ctx, 9, 12, 15, 18)
            } else if (root.name === "chevron-right") {
                line(ctx, 9, 6, 15, 12)
                line(ctx, 15, 12, 9, 18)
            } else if (root.name === "info") {
                ctx.arc(12, 12, 7.5, 0, Math.PI * 2)
                line(ctx, 12, 10.5, 12, 16.5)
                ctx.moveTo(13, 7.5)
                ctx.arc(12, 7.5, 1, 0, Math.PI * 2)
            } else if (root.name === "trash") {
                ctx.rect(7, 8, 10, 11)
                line(ctx, 5.5, 6.5, 18.5, 6.5)
                line(ctx, 9.5, 4.5, 14.5, 4.5)
                line(ctx, 10, 10.5, 10, 16)
                line(ctx, 14, 10.5, 14, 16)
            } else if (root.name === "up") {
                line(ctx, 6, 14.5, 12, 8.5)
                line(ctx, 12, 8.5, 18, 14.5)
            } else if (root.name === "down") {
                line(ctx, 6, 9.5, 12, 15.5)
                line(ctx, 12, 15.5, 18, 9.5)
            } else if (root.name === "folder") {
                // Modern file folder with clean tab
                ctx.moveTo(3.5, 7)
                ctx.lineTo(9, 7)
                ctx.lineTo(11, 9.5)
                ctx.lineTo(20.5, 9.5)
                ctx.lineTo(20.5, 18.5)
                ctx.lineTo(3.5, 18.5)
                ctx.closePath()
            } else if (root.name === "artist") {
                // Precision user portrait
                ctx.arc(12, 8, 3.5, 0, Math.PI * 2)
                ctx.moveTo(18.5, 19.5)
                ctx.arc(12, 19.5, 6.5, Math.PI, Math.PI * 2)
            } else if (root.name === "genre") {
                // Symmetrical metadata / audio tag
                ctx.moveTo(4.5, 7.5)
                ctx.lineTo(13.5, 7.5)
                ctx.lineTo(19.5, 12)
                ctx.lineTo(13.5, 16.5)
                ctx.lineTo(4.5, 16.5)
                ctx.closePath()
                ctx.moveTo(9, 12)
                ctx.arc(8, 12, 1, 0, Math.PI * 2)
            } else if (root.name === "more") {
                ctx.arc(6, 12, 1.5, 0, Math.PI * 2)
                ctx.moveTo(13.5, 12)
                ctx.arc(12, 12, 1.5, 0, Math.PI * 2)
                ctx.moveTo(19.5, 12)
                ctx.arc(18, 12, 1.5, 0, Math.PI * 2)
                ctx.fill()
                ctx.restore()
                return
            } else if (root.name === "home") {
                ctx.moveTo(4.5, 11.5)
                ctx.lineTo(12, 5)
                ctx.lineTo(19.5, 11.5)
                ctx.moveTo(6.5, 10)
                ctx.lineTo(6.5, 19)
                ctx.lineTo(17.5, 19)
                ctx.lineTo(17.5, 10)
            } else {
                ctx.arc(12, 12, 7, 0, Math.PI * 2)
            }
            ctx.stroke()
            ctx.restore()
        }
    }
}
