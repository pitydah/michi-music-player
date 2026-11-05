import QtQuick
import QtQuick.Shapes

/*
 * Michi Signal Truth stage glyphs. Official Tabler Icons geometry (MIT).
 * Source: https://github.com/tabler/tabler-icons/tree/main/icons/outline
 * Assets and SHA-256 provenance live in src/michi/resources/icons/tabler/.
 * Copyright (c) 2020-2026 Paweł Kuna and Tabler Icons contributors.
 *
 * MIT License applies to the referenced glyphs; see the bundled LICENSE file.
 */
Item {
    id: root
    property string roleName: "track"
    property color iconColor: "#ECEEF3"
    implicitWidth: 24
    implicitHeight: 24
    Accessible.role: Accessible.Graphic
    Accessible.name: root.roleName

    readonly property var paths: ({

        "adjustments-horizontal": "M12 6a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M4 6l8 0 M16 6l4 0 M6 12a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M4 12l2 0 M10 12l10 0 M15 18a2 2 0 1 0 4 0a2 2 0 1 0 -4 0 M4 18l11 0 M19 18l1 0",
        "alert-triangle": "M12 9v4 M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0 M12 16h.01",
        "arrows-exchange": "M7 10h14l-4 -4 M17 14h-14l4 4",
        "binary": "M11 10v-5h-1m8 14v-5h-1 M15 5.5a.5 .5 0 0 1 .5 -.5h2a.5 .5 0 0 1 .5 .5v4a.5 .5 0 0 1 -.5 .5h-2a.5 .5 0 0 1 -.5 -.5l0 -4 M10 14.5a.5 .5 0 0 1 .5 -.5h2a.5 .5 0 0 1 .5 .5v4a.5 .5 0 0 1 -.5 .5h-2a.5 .5 0 0 1 -.5 -.5l0 -4 M6 10h.01m-.01 9h.01",
        "circuit-diode": "M22 12h-6 M2 12h6 M8 7l8 5l-8 5l0 -10 M16 7v10",
        "cpu": "M5 6a1 1 0 0 1 1 -1h12a1 1 0 0 1 1 1v12a1 1 0 0 1 -1 1h-12a1 1 0 0 1 -1 -1l0 -12 M9 9h6v6h-6l0 -6 M3 10h2 M3 14h2 M10 3v2 M14 3v2 M21 10h-2 M21 14h-2 M14 21v-2 M10 21v-2",
        "device-speaker": "M5 5a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2l0 -14 M9 14a3 3 0 1 0 6 0a3 3 0 1 0 -6 0 M12 7l0 .01",
        "file-music": "M14 3v4a1 1 0 0 0 1 1h4 M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2 M10 16a1 1 0 1 0 2 0a1 1 0 1 0 -2 0 M12 16l0 -5l2 1",
        "headphones": "M4 15a2 2 0 0 1 2 -2h1a2 2 0 0 1 2 2v3a2 2 0 0 1 -2 2h-1a2 2 0 0 1 -2 -2l0 -3 M15 15a2 2 0 0 1 2 -2h1a2 2 0 0 1 2 2v3a2 2 0 0 1 -2 2h-1a2 2 0 0 1 -2 -2l0 -3 M4 15v-3a8 8 0 0 1 16 0v3",
        "plug-connected": "M7 12l5 5l-1.5 1.5a3.536 3.536 0 1 1 -5 -5l1.5 -1.5 M17 12l-5 -5l1.5 -1.5a3.536 3.536 0 1 1 5 5l-1.5 1.5 M3 21l2.5 -2.5 M18.5 5.5l2.5 -2.5 M10 11l-2 2 M13 14l-2 2",
        "wave-sine": "M21 12h-2c-.894 0 -1.662 -.857 -1.761 -2c-.296 -3.45 -.749 -6 -2.749 -6s-2.5 3.582 -2.5 8s-.5 8 -2.5 8s-2.452 -2.547 -2.749 -6c-.1 -1.147 -.867 -2 -1.763 -2h-2",
    })
    readonly property var aliases: ({

        "adjustments-horizontal": "adjustments-horizontal",
        "alert-triangle": "alert-triangle",
        "arrows-exchange": "arrows-exchange",
        "audio-engine": "cpu",
        "audio-output": "wave-sine",
        "binary": "binary",
        "channel-remap": "arrows-exchange",
        "circuit-diode": "circuit-diode",
        "cpu": "cpu",
        "dac": "circuit-diode",
        "decode": "cpu",
        "device": "circuit-diode",
        "device-speaker": "device-speaker",
        "equalizer": "adjustments-horizontal",
        "error": "alert-triangle",
        "file-music": "file-music",
        "fir": "adjustments-horizontal",
        "headphones": "headphones",
        "output": "wave-sine",
        "plug-connected": "plug-connected",
        "processing": "adjustments-horizontal",
        "resample": "arrows-exchange",
        "sliders": "adjustments-horizontal",
        "source": "file-music",
        "track": "file-music",
        "wave-sine": "wave-sine",
    })
    readonly property string resolvedRole: aliases[roleName] || "device-speaker"
    readonly property string pathData: paths[resolvedRole] || paths["device-speaker"]

    readonly property bool curveRendererActive:
        shape.rendererType === Shape.CurveRenderer

    Shape {
        id: shape
        anchors.fill: parent
        antialiasing: true
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.iconColor
            fillColor: "transparent"
            strokeWidth: 2.0
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.pathData }
        }
    }
}
