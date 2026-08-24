import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

/* M6.9 — EnrichmentAttribution: truthful provenance rows. Every field is
 * projected by the bridge only when the backend actually provided it;
 * nothing is invented here. External links open ONLY when the scheme is
 * https:// (fail closed). */
ColumnLayout {
    id: root

    property var sources: [] // list of dicts: provider/sourceUrl/license/licenseUrl/attribution/retrievedAt/isStale

    spacing: MichiSpacing.xs
    onSourcesChanged: root.visible = root.sources.length > 0

    function isSafeUrl(url) {
        return typeof url === "string" && url.length > 0 && url.startsWith("https://")
    }

    function openSafe(url) {
        if (root.isSafeUrl(url))
            Qt.openUrlExternally(url)
    }

    MichiText {
        text: "Sources"
        role: "caption"
        color: MichiPalette.textMuted
    }

    Repeater {
        model: root.sources
        delegate: RowLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiText {
                text: modelData.provider || "unknown"
                role: "technical"
                color: MichiPalette.textSecondary
            }

            MichiText {
                text: modelData.license || ""
                role: "technical"
                color: MichiPalette.textMuted
                visible: text.length > 0
            }

            MichiText {
                text: modelData.retrievedAt || ""
                role: "technical"
                color: MichiPalette.textMuted
                visible: text.length > 0
            }

            MichiText {
                text: "saved information may be outdated"
                role: "technical"
                color: MichiPalette.warning
                visible: modelData.isStale === true
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                text: "Open source"
                variant: "ghost"
                visible: root.isSafeUrl(modelData.sourceUrl)
                Accessible.name: "Open " + (modelData.provider || "source")
                onClicked: root.openSafe(modelData.sourceUrl)
            }
        }
    }
}
