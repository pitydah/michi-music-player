import QtQuick
import QtQuick.Window

// PL-FINAL-09 + PL-10-FINAL-10 — reusable focal-aware crop renderer for
// hero imagery, DPR-aware.
//
// Model (per the playlist focal contract):
//   - preserve the original aspect ratio;
//   - scale = max(containerW / sourceW, containerH / sourceH) so the
//     image always covers the container;
//   - position so the NORMALIZED focal coordinate stays the visual
//     anchor:  x = clamp(containerW*focalX - renderedW*focalX, ...)
//     clamped so no blank region becomes visible.
// Handles a not-yet-loaded source without warnings or NaN (scale 1,
// neutral position).
//
// Decode policy (PL-10-FINAL-10): requested sourceSize derives from the
// VIEWPORT × devicePixelRatio, clamped to hard safety caps — a wide 4K
// hero decodes enough detail without decoding the full original.
Item {
    id: root

    property string source: ""
    property real focalX: 0.5
    property real focalY: 0.5
    // DPR-aware decode caps (safe ceiling; viewport*DPR usually far below).
    property real decodeDpr:
        Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1.0
    property int maxDecodeWidth: 5120
    property int maxDecodeHeight: 2880

    readonly property int requestedDecodeWidth: Math.max(
        1,
        Math.min(
            root.maxDecodeWidth,
            Math.ceil(root.width * root.decodeDpr)
        )
    )
    readonly property int requestedDecodeHeight: Math.max(
        1,
        Math.min(
            root.maxDecodeHeight,
            Math.ceil(root.height * root.decodeDpr)
        )
    )

    readonly property real _sourceW: img.sourceSize.width > 0
        ? img.sourceSize.width : 1
    readonly property real _sourceH: img.sourceSize.height > 0
        ? img.sourceSize.height : 1
    readonly property real _scale: Math.max(
        root.width / root._sourceW, root.height / root._sourceH)
    readonly property real _renderedW: root._sourceW * root._scale
    readonly property real _renderedH: root._sourceH * root._scale
    readonly property real _x: Math.min(0, Math.max(
        root.width - root._renderedW,
        root.width * root.focalX - root._renderedW * root.focalX))
    readonly property real _y: Math.min(0, Math.max(
        root.height - root._renderedH,
        root.height * root.focalY - root._renderedH * root.focalY))

    clip: true

    Image {
        id: img
        x: root._x
        y: root._y
        width: root._renderedW
        height: root._renderedH
        visible: root.source.length > 0
        source: root.source
        sourceSize.width: root.requestedDecodeWidth
        sourceSize.height: root.requestedDecodeHeight
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectFit
    }
}
