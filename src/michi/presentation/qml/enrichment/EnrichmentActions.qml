import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

/* M6.9 — EnrichmentActions: contextual action row. Network actions
 * (refresh / review) only appear when online enrichment is ON; local
 * actions (clear online info / reset match) stay available offline. */
RowLayout {
    id: root

    property string kind: "artist"
    property string state: "IDLE"
    property bool onlineEnabled: true
    property bool hasKnowledge: false

    signal refreshRequested()
    signal reviewRequested()
    signal clearRequested()
    signal resetRequested()

    spacing: MichiSpacing.sm
    visible: root.kind === "artist" || root.kind === "album"

    function _showReview() {
        return root.onlineEnabled
            && (root.state === "AMBIGUOUS" || root.state === "NOT_FOUND")
    }

    function _showRefresh() {
        return root.onlineEnabled
            && root.state !== "RESOLVING_IDENTITY"
            && root.state !== "FETCHING_KNOWLEDGE"
    }

    MichiButton {
        text: "Review match"
        variant: "ghost"
        visible: root._showReview()
        Accessible.name: "Review " + root.kind + " match"
        onClicked: root.reviewRequested()
    }

    MichiButton {
        text: root.hasKnowledge ? "Refresh" : "Fetch online info"
        variant: "ghost"
        visible: root._showRefresh()
        Accessible.name: root.hasKnowledge ? "Refresh online information" : "Fetch online information"
        onClicked: root.refreshRequested()
    }

    MichiButton {
        text: "Clear online info"
        variant: "ghost"
        visible: root.hasKnowledge
        Accessible.name: "Clear online information"
        onClicked: root.clearRequested()
    }

    MichiButton {
        text: "Reset match"
        variant: "ghost"
        Accessible.name: "Reset " + root.kind + " match"
        onClicked: root.resetRequested()
    }
}
