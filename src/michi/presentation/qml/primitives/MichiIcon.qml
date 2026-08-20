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
            ctx.moveTo(x1, y1); ctx.lineTo(x2, y2)
        }

        onPaint: {
            var ctx = getContext("2d")
            var w = width; var h = height; var cx = w / 2; var cy = h / 2
            ctx.reset()
            ctx.strokeStyle = root.iconColor
            ctx.fillStyle = root.iconColor
            ctx.lineWidth = root.strokeWidth
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.beginPath()
            if (root.name === "play") {
                ctx.moveTo(w * .34, h * .23); ctx.lineTo(w * .76, cy); ctx.lineTo(w * .34, h * .77); ctx.closePath(); ctx.fill(); return
            } else if (root.name === "pause") {
                ctx.fillRect(w * .3, h * .24, w * .13, h * .52); ctx.fillRect(w * .57, h * .24, w * .13, h * .52); return
            } else if (root.name === "stop") {
                ctx.fillRect(w * .28, h * .28, w * .44, h * .44); return
            } else if (root.name === "previous") {
                ctx.fillRect(w * .22, h * .25, w * .08, h * .5); ctx.moveTo(w * .72, h * .25); ctx.lineTo(w * .34, cy); ctx.lineTo(w * .72, h * .75); ctx.closePath(); ctx.fill(); return
            } else if (root.name === "next") {
                ctx.fillRect(w * .7, h * .25, w * .08, h * .5); ctx.moveTo(w * .28, h * .25); ctx.lineTo(w * .66, cy); ctx.lineTo(w * .28, h * .75); ctx.closePath(); ctx.fill(); return
            } else if (root.name === "output-status") {
                ctx.moveTo(w * .18, h * .42); ctx.lineTo(w * .34, h * .42); ctx.lineTo(w * .52, h * .26); ctx.lineTo(w * .52, h * .74); ctx.lineTo(w * .34, h * .58); ctx.lineTo(w * .18, h * .58); ctx.closePath(); ctx.moveTo(w * .64, h * .4); ctx.arc(w * .57, cy, w * .18, -.65, .65); ctx.moveTo(w * .79, h * .24); ctx.arc(w * .62, cy, w * .3, -.85, .85)
            } else if (root.name === "volume" || root.name === "mute") {
                ctx.moveTo(w * .2, h * .42); ctx.lineTo(w * .36, h * .42); ctx.lineTo(w * .55, h * .25); ctx.lineTo(w * .55, h * .75); ctx.lineTo(w * .36, h * .58); ctx.lineTo(w * .2, h * .58); ctx.closePath();
                if (root.name === "volume") { ctx.moveTo(w * .65, h * .38); ctx.arc(w * .58, cy, w * .2, -.7, .7) }
                else { line(ctx, w * .65, h * .37, w * .83, h * .63); line(ctx, w * .83, h * .37, w * .65, h * .63) }
            } else if (root.name === "search") {
                ctx.arc(w * .43, h * .43, w * .24, 0, Math.PI * 2); line(ctx, w * .61, h * .61, w * .82, h * .82)
            } else if (root.name === "library") {
                ctx.rect(w * .2, h * .22, w * .15, h * .58); ctx.rect(w * .43, h * .16, w * .15, h * .64); ctx.rect(w * .66, h * .28, w * .15, h * .52)
            } else if (root.name === "view-grid") {
                ctx.rect(w * .18, h * .18, w * .25, h * .25); ctx.rect(w * .57, h * .18, w * .25, h * .25); ctx.rect(w * .18, h * .57, w * .25, h * .25); ctx.rect(w * .57, h * .57, w * .25, h * .25)
            } else if (root.name === "view-path") {
                ctx.rect(w * .2, h * .29, w * .42, h * .48); ctx.rect(w * .38, h * .2, w * .42, h * .48); line(ctx, w * .26, h * .68, w * .52, h * .68)
            } else if (root.name === "view-vinyl") {
                ctx.arc(cx, cy, w * .32, 0, Math.PI * 2); ctx.moveTo(w * .62, cy); ctx.arc(cx, cy, w * .12, 0, Math.PI * 2); ctx.moveTo(cx + 1, cy); ctx.arc(cx, cy, 1.5, 0, Math.PI * 2)
            } else if (root.name === "view-timeline") {
                line(ctx, w * .3, h * .16, w * .3, h * .84); ctx.moveTo(w * .36, h * .28); ctx.arc(w * .3, h * .28, w * .06, 0, Math.PI * 2); ctx.moveTo(w * .36, h * .52); ctx.arc(w * .3, h * .52, w * .06, 0, Math.PI * 2); ctx.moveTo(w * .36, h * .76); ctx.arc(w * .3, h * .76, w * .06, 0, Math.PI * 2); line(ctx, w * .43, h * .28, w * .8, h * .28); line(ctx, w * .43, h * .52, w * .72, h * .52); line(ctx, w * .43, h * .76, w * .78, h * .76)
            } else if (root.name === "view-magazine") {
                ctx.rect(w * .17, h * .2, w * .4, h * .6); ctx.rect(w * .64, h * .2, w * .19, h * .22); line(ctx, w * .64, h * .53, w * .83, h * .53); line(ctx, w * .64, h * .66, w * .83, h * .66); line(ctx, w * .64, h * .79, w * .78, h * .79)
            } else if (root.name === "view-list") {
                ctx.rect(w * .18, h * .2, w * .13, h * .13); ctx.rect(w * .18, h * .44, w * .13, h * .13); ctx.rect(w * .18, h * .68, w * .13, h * .13); line(ctx, w * .4, h * .265, w * .82, h * .265); line(ctx, w * .4, h * .505, w * .82, h * .505); line(ctx, w * .4, h * .745, w * .82, h * .745)
            } else if (root.name === "density-comfortable") {
                line(ctx, w * .22, h * .28, w * .78, h * .28); line(ctx, w * .22, h * .72, w * .78, h * .72)
            } else if (root.name === "density-standard") {
                line(ctx, w * .22, h * .25, w * .78, h * .25); line(ctx, w * .22, cy, w * .78, cy); line(ctx, w * .22, h * .75, w * .78, h * .75)
            } else if (root.name === "density-compact") {
                line(ctx, w * .22, h * .22, w * .78, h * .22); line(ctx, w * .22, h * .41, w * .78, h * .41); line(ctx, w * .22, h * .59, w * .78, h * .59); line(ctx, w * .22, h * .78, w * .78, h * .78)
            } else if (root.name === "queue") {
                line(ctx, w * .2, h * .28, w * .72, h * .28); line(ctx, w * .2, h * .5, w * .72, h * .5); line(ctx, w * .2, h * .72, w * .55, h * .72); ctx.moveTo(w * .66, h * .62); ctx.lineTo(w * .84, h * .72); ctx.lineTo(w * .66, h * .82); ctx.closePath()
            } else if (root.name === "shuffle") {
                ctx.moveTo(w * .18, h * .3); ctx.lineTo(w * .31, h * .3); ctx.bezierCurveTo(w * .45, h * .3, w * .53, h * .7, w * .68, h * .7); line(ctx, w * .68, h * .7, w * .82, h * .7); line(ctx, w * .72, h * .6, w * .82, h * .7); line(ctx, w * .72, h * .8, w * .82, h * .7); ctx.moveTo(w * .18, h * .7); ctx.lineTo(w * .31, h * .7); ctx.bezierCurveTo(w * .45, h * .7, w * .53, h * .3, w * .68, h * .3); line(ctx, w * .68, h * .3, w * .82, h * .3); line(ctx, w * .72, h * .2, w * .82, h * .3); line(ctx, w * .72, h * .4, w * .82, h * .3)
            } else if (root.name === "repeat" || root.name === "repeat-one") {
                ctx.moveTo(w * .25, h * .34); ctx.lineTo(w * .7, h * .34); line(ctx, w * .61, h * .25, w * .7, h * .34); line(ctx, w * .61, h * .43, w * .7, h * .34); ctx.arc(cx, cy, w * .3, -.7, Math.PI - .45); ctx.moveTo(w * .75, h * .66); ctx.lineTo(w * .3, h * .66); line(ctx, w * .39, h * .57, w * .3, h * .66); line(ctx, w * .39, h * .75, w * .3, h * .66); if (root.name === "repeat-one") { ctx.stroke(); ctx.beginPath(); ctx.font = Math.round(h * .36) + "px sans-serif"; ctx.fillText("1", w * .44, h * .61); return }
            } else if (root.name === "sliders") {
                line(ctx, w * .27, h * .18, w * .27, h * .82); line(ctx, cx, h * .18, cx, h * .82); line(ctx, w * .73, h * .18, w * .73, h * .82); ctx.moveTo(w * .2, h * .36); ctx.lineTo(w * .34, h * .36); ctx.moveTo(w * .43, h * .62); ctx.lineTo(w * .57, h * .62); ctx.moveTo(w * .66, h * .42); ctx.lineTo(w * .8, h * .42)
            } else if (root.name === "device") {
                ctx.rect(w * .25, h * .15, w * .5, h * .7); ctx.moveTo(w * .4, h * .27); ctx.lineTo(w * .6, h * .27); ctx.arc(cx, h * .58, w * .1, 0, Math.PI * 2); ctx.fillRect(cx - 1, h * .77, 2, 2)
            } else if (root.name === "settings") {
                ctx.arc(cx, cy, w * .17, 0, Math.PI * 2); ctx.moveTo(cx, h * .12); ctx.lineTo(cx, h * .24); ctx.moveTo(cx, h * .76); ctx.lineTo(cx, h * .88); ctx.moveTo(w * .12, cy); ctx.lineTo(w * .24, cy); ctx.moveTo(w * .76, cy); ctx.lineTo(w * .88, cy)
            } else if (root.name === "heart") {
                ctx.moveTo(cx, h * .82); ctx.bezierCurveTo(w * .18, h * .62, w * .12, h * .35, w * .31, h * .25); ctx.bezierCurveTo(w * .43, h * .19, cx, h * .29, cx, h * .36); ctx.bezierCurveTo(cx, h * .29, w * .57, h * .19, w * .69, h * .25); ctx.bezierCurveTo(w * .88, h * .35, w * .82, h * .62, cx, h * .82)
            } else if (root.name === "history") {
                ctx.arc(cx, cy, w * .31, -.35, Math.PI * 1.65); line(ctx, cx, cy, cx, h * .31); line(ctx, cx, cy, w * .67, h * .58); line(ctx, w * .19, h * .2, w * .2, h * .4); line(ctx, w * .19, h * .2, w * .39, h * .21)
            } else if (root.name === "close") {
                line(ctx, w * .25, h * .25, w * .75, h * .75); line(ctx, w * .75, h * .25, w * .25, h * .75)
            } else if (root.name === "add") {
                line(ctx, cx, h * .22, cx, h * .78); line(ctx, w * .22, cy, w * .78, cy)
            } else if (root.name === "info") {
                ctx.arc(cx, cy, w * .32, 0, Math.PI * 2); line(ctx, cx, h * .43, cx, h * .72); ctx.fillRect(cx - 1, h * .27, 2, 2)
            } else if (root.name === "trash") {
                ctx.rect(w * .3, h * .31, w * .4, h * .5); line(ctx, w * .23, h * .25, w * .77, h * .25); line(ctx, w * .4, h * .18, w * .6, h * .18); line(ctx, w * .42, h * .42, w * .42, h * .68); line(ctx, w * .58, h * .42, w * .58, h * .68)
            } else if (root.name === "up") {
                line(ctx, w * .24, h * .62, cx, h * .36); line(ctx, cx, h * .36, w * .76, h * .62)
            } else if (root.name === "down") {
                line(ctx, w * .24, h * .38, cx, h * .64); line(ctx, cx, h * .64, w * .76, h * .38)
            } else if (root.name === "folder") {
                ctx.moveTo(w * .17, h * .3); ctx.lineTo(w * .42, h * .3); ctx.lineTo(w * .5, h * .4); ctx.lineTo(w * .83, h * .4); ctx.lineTo(w * .83, h * .76); ctx.lineTo(w * .17, h * .76); ctx.closePath()
            } else if (root.name === "artist") {
                ctx.arc(cx, h * .34, w * .16, 0, Math.PI * 2); ctx.arc(cx, h * .83, w * .29, Math.PI, Math.PI * 2)
            } else if (root.name === "genre") {
                ctx.moveTo(w * .18, h * .31); ctx.lineTo(w * .61, h * .31); ctx.lineTo(w * .82, cy); ctx.lineTo(w * .61, h * .69); ctx.lineTo(w * .18, h * .69); ctx.closePath(); ctx.moveTo(w * .3, cy); ctx.arc(w * .3, cy, 1.5, 0, Math.PI * 2)
            } else if (root.name === "more") {
                ctx.fillRect(w * .2, cy - 1, 2, 2); ctx.fillRect(cx - 1, cy - 1, 2, 2); ctx.fillRect(w * .8 - 2, cy - 1, 2, 2); return
            } else if (root.name === "home") {
                ctx.moveTo(w * .18, h * .48); ctx.lineTo(cx, h * .18); ctx.lineTo(w * .82, h * .48); ctx.moveTo(w * .27, h * .4); ctx.lineTo(w * .27, h * .82); ctx.lineTo(w * .73, h * .82); ctx.lineTo(w * .73, h * .4)
            } else {
                ctx.arc(cx, cy, w * .29, 0, Math.PI * 2)
            }
            ctx.stroke()
        }
    }
}
