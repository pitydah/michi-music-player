import QtQuick

// PL-FINAL-09 — reusable focal-aware crop renderer for hero imagery.
//
// Model (per the playlist focal contract):
//   - preserve the original aspect ratio;
//   - scale = max(containerW / sourceW, containerH / sourceH) so the
//     image always covers the container;
//   - position so the NORMALIZED focal coordinate stays the visual
//     anchor:  x = clamp(containerW*focalX - renderedW*focalX, ...)
//     clamped so no blank region becomes visible.
// Handles a not-yet-loaded source without warnings or NaN (scale 1,
// neutral position), and never decodes more than maxWidth x maxHeight.
Item {
    id: root

    property string source: ""
    property real focalX: 0.5
    property real focalY: 0.5
    property int maxWidth: 3200
    property int maxHeight: 1200

    clip: true

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

    Image {
        id: img
        x: root._x
        y: root._y
        width: root._renderedW
        height: root._renderedH
        visible: root.source.length > 0
        source: root.source
        sourceSize.width: root.maxWidth
        sourceSize.height: root.maxHeight
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectFit
    }
}
