import QtQuick
import MichiCover 1.0

CoverBridge {
    id: root
    property bool ready: false
    onCoverChanged: ready = true
}
