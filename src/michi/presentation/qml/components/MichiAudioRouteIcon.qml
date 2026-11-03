import QtQuick
import "../theme"

// Michi original 24-unit audio-route pictograms. No icon font, network or
// extra QtSvg dependency. Identity glyphs never encode 'active' by shape.
Item {
    id: root
    property string roleName: "dac"
    property color iconColor: MichiPalette.textSecondary
    implicitWidth: 20
    implicitHeight: 20
    Accessible.role: Accessible.Graphic
    Accessible.name: roleName
    onRoleNameChanged: glyph.requestPaint()
    onIconColorChanged: glyph.requestPaint()
    Canvas {
        id: glyph
        anchors.fill: parent
        antialiasing: true
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (width < 1 || height < 1) return
            ctx.save()
            ctx.scale(width / 24, height / 24)
            ctx.lineWidth = 1.65
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.strokeStyle = root.iconColor
            ctx.fillStyle = root.iconColor
            function segment(x1,y1,x2,y2) {
                ctx.moveTo(x1,y1); ctx.lineTo(x2,y2)
            }
            function rounded(x,y,w,h,r) {
                ctx.moveTo(x+r,y)
                ctx.lineTo(x+w-r,y)
                ctx.quadraticCurveTo(x+w,y,x+w,y+r)
                ctx.lineTo(x+w,y+h-r)
                ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h)
                ctx.lineTo(x+r,y+h)
                ctx.quadraticCurveTo(x,y+h,x,y+h-r)
                ctx.lineTo(x,y+r)
                ctx.quadraticCurveTo(x,y,x+r,y)
                ctx.closePath()
            }
            ctx.beginPath()
            var key = root.roleName.toLowerCase()
            if (key === "engine") {
                rounded(5.5,5.5,13,13,2)
                ctx.rect(9,9,6,6)
                for (var i=8;i<=16;i+=4) {
                    segment(i,3.5,i,5.5);segment(i,18.5,i,20.5)
                    segment(3.5,i,5.5,i);segment(18.5,i,20.5,i)
                }
            } else if (key === "qt") {
                rounded(4,5,16,13,2)
                segment(4,9,20,9)
                segment(9,13.5,12,16); segment(12,16,15.5,12.5)
            } else if (key === "gstreamer") {
                ctx.moveTo(3.5,12)
                ctx.bezierCurveTo(6,12,6,6.5,8.5,6.5)
                ctx.bezierCurveTo(11,6.5,10.5,17.5,13.5,17.5)
                ctx.bezierCurveTo(16,17.5,15.5,12,20.5,12)
                segment(18,9.5,20.5,12);segment(18,14.5,20.5,12)
            } else if (key === "mpd") {
                rounded(4,3.5,16,17,2)
                segment(4,9,20,9);segment(4,14.5,20,14.5)
                for (var s=6.5;s<=17.5;s+=5.5) {
                    ctx.moveTo(7, s);ctx.arc(7,s,0.65,0,Math.PI*2)
                    segment(11,s,16.5,s)
                }
            } else if (key === "system") {
                rounded(3.5,4.5,17,12.5,2)
                segment(12,17,12,20);segment(7.5,20,16.5,20)
            } else if (key === "display") {
                rounded(3,5,18,13,2)
                segment(8,21,16,21);segment(12,18,12,21)
                segment(8,10,16,10);segment(10,13,14,13)
            } else if (key === "usb") {
                segment(12,19,12,6)
                segment(12,6,9.5,8.5);segment(12,6,14.5,8.5)
                segment(12,6,12,3)
                segment(12,14,6.5,14);segment(6.5,14,6.5,11)
                segment(12,10,18,10);segment(18,10,18,13)
                ctx.rect(16.5,13,3,3)
                ctx.moveTo(6.5,10);ctx.arc(6.5,10,1,0,Math.PI*2)
            } else if (key === "internal") {
                rounded(6,6,12,12,2)
                ctx.moveTo(12,12);ctx.arc(12,12,3,0,Math.PI*2)
                for (var k=8;k<=16;k+=4) {
                    segment(k,4,k,6); segment(k,18,k,20)
                }
            } else {
                // DAC: converter chassis, input trace, output wave.
                rounded(3.5,5.5,17,13,2)
                segment(5.5,12,9.5,12)
                ctx.moveTo(10,12)
                ctx.bezierCurveTo(11.5,12,11.5,9,13,9)
                ctx.bezierCurveTo(14.5,9,14.5,15,16,15)
                segment(16,15,18.5,15)
            }
            ctx.stroke()
            ctx.restore()
        }
    }
}
