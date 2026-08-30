import QtQuick

// R2 P1-05 presentation-safe persistence failure connector.
//
// Lives OUTSIDE shell/ContentHost.qml on purpose: a Connections target
// named `playlists` inside a file that ALSO imports "../playlists" (the
// directory module) makes the QML signal detector emit a spurious
// "no signal matches" warning. This component imports no conflicting
// module, so `target: playlists` resolves to the bridge context property
// and the signal matches cleanly.
Connections {
    id: root

    target: playlists

    // (operationCode) => human text — supplied by the host (qsTr lives
    // in the host scope).
    property var failureMessageFor: null
    // (text) => void — supplied by the host (window.showToast etc.).
    property var notify: null

    function onMutationFailed(operationCode) {
        if (root.failureMessageFor && root.notify)
            root.notify(root.failureMessageFor(operationCode))
    }
}
