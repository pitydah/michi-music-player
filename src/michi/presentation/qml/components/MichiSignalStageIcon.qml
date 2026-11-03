import QtQuick
import "../theme"

/*
 * Signal Truth semantic glyphs adapted from Tabler Icons (MIT).
 * Source: https://github.com/tabler/tabler-icons
 * Original glyphs: file-music, wave-square, adjustments-horizontal,
 * wave-sine, device-speaker. Geometry adjusted to Michi's 1.7px stroke.
 * Copyright (c) 2020-2026 Paweł Kuna and Tabler Icons contributors.
 *
 * MIT License
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

// Dedicated semantics, independent of evidence status. Designed for the
// 19-20px stage glyph without raster assets, runtime downloads or QtSvg.
Item {
    id: root
    property string roleName: "track"
    property color iconColor: MichiPalette.textPrimary
    implicitWidth: 20
    implicitHeight: 20
    Accessible.role: Accessible.Graphic
    Accessible.name: root.roleName
    onRoleNameChanged: canvas.requestPaint()
    onIconColorChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var c = getContext("2d")
            c.reset()
            if (width <= 0 || height <= 0) return
            c.save()
            c.scale(width / 24, height / 24)
            c.strokeStyle = root.iconColor
            c.fillStyle = root.iconColor
            c.lineWidth = 1.7
            c.lineJoin = "round"
            c.lineCap = "round"
            c.beginPath()
            var role = root.roleName
            if (role === "track") {
                // Tabler file-music: source container / recorded media.
                c.moveTo(14, 3); c.lineTo(14, 7); c.quadraticCurveTo(14, 8, 15, 8)
                c.lineTo(19, 8); c.moveTo(14, 3); c.lineTo(7, 3)
                c.quadraticCurveTo(5, 3, 5, 5); c.lineTo(5, 19)
                c.quadraticCurveTo(5, 21, 7, 21); c.lineTo(17, 21)
                c.quadraticCurveTo(19, 21, 19, 19); c.lineTo(19, 8)
                c.lineTo(14, 3); c.moveTo(12, 16); c.lineTo(12, 11)
                c.lineTo(14, 12); c.moveTo(12, 16)
                c.arc(11, 16, 1, 0, Math.PI * 2)
            } else if (role === "audio-engine" || role === "channel-remap") {
                // Tabler wave-square: decoded digital PCM.
                c.moveTo(3, 12); c.lineTo(8, 12); c.lineTo(8, 20)
                c.lineTo(12, 20); c.lineTo(12, 4); c.lineTo(16, 4)
                c.lineTo(16, 12); c.lineTo(21, 12)
            } else if (role === "equalizer" || role === "sliders") {
                // Tabler adjustments-horizontal: gain/frequency stage.
                c.moveTo(4, 6); c.lineTo(12, 6)
                c.moveTo(16, 6); c.lineTo(20, 6)
                c.moveTo(4, 12); c.lineTo(6, 12)
                c.moveTo(10, 12); c.lineTo(20, 12)
                c.moveTo(4, 18); c.lineTo(15, 18)
                c.moveTo(19, 18); c.lineTo(20, 18)
                c.moveTo(14, 4); c.arc(14, 6, 2, -Math.PI / 2, Math.PI * 1.5)
                c.moveTo(8, 10); c.arc(8, 12, 2, -Math.PI / 2, Math.PI * 1.5)
                c.moveTo(17, 16); c.arc(17, 18, 2, -Math.PI / 2, Math.PI * 1.5)
            } else if (role === "audio-output" || role === "resample") {
                // Tabler wave-sine simplified: transport signal.
                c.moveTo(2, 12); c.lineTo(5, 12)
                c.bezierCurveTo(9, 12, 7, 20, 10, 20)
                c.bezierCurveTo(13, 20, 11, 4, 14, 4)
                c.bezierCurveTo(17, 4, 15, 12, 19, 12)
                c.lineTo(22, 12)
            } else {
                // Tabler device-speaker: physical DAC / connected device.
                c.moveTo(7, 3); c.lineTo(17, 3)
                c.quadraticCurveTo(19, 3, 19, 5); c.lineTo(19, 19)
                c.quadraticCurveTo(19, 21, 17, 21); c.lineTo(7, 21)
                c.quadraticCurveTo(5, 21, 5, 19); c.lineTo(5, 5)
                c.quadraticCurveTo(5, 3, 7, 3)
                c.moveTo(15, 14); c.arc(12, 14, 3, 0, Math.PI * 2)
                c.moveTo(12, 7); c.arc(12, 7, .35, 0, Math.PI * 2)
            }
            c.stroke()
            c.restore()
        }
    }
}
