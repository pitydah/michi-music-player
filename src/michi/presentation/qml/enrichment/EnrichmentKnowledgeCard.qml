import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

/* M6.9 — EnrichmentKnowledgeCard: premium glass surface presenting the
 * external knowledge projection. Only fields that really exist are shown
 * (the bridge never invents facts). Biography is plain text with a
 * bounded preview + Show more/Show less. */
MichiGlassSurface {
    id: root

    property string title: "Online information"
    property var knowledge: ({})
    property bool hasKnowledge: false
    property var sources: []

    Layout.fillWidth: true
    elevation: "standard"

    contentPadding: MichiSpacing.lg

    implicitHeight: content.implicitHeight + MichiSpacing.lg * 2

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: MichiSpacing.lg
        spacing: MichiSpacing.md
        visible: root.hasKnowledge

        MichiText {
            text: root.title
            role: "section"
        }

        /* biography — plain text, bounded preview, no remote markup */
        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            visible: (root.knowledge.biography || "").length > 0

            readonly property string biography: root.knowledge.biography || ""
            property bool expanded: false

            MichiText {
                Layout.fillWidth: true
                text: parent.expanded
                    ? parent.biography
                    : parent.biography.length > 420
                        ? parent.biography.slice(0, 420) + "…"
                        : parent.biography
                role: "body"
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }

            MichiButton {
                text: parent.biography.length > 420
                    ? (parent.expanded ? "Show less" : "Show more")
                    : ""
                variant: "ghost"
                visible: text.length > 0
                Layout.alignment: Qt.AlignLeft
                onClicked: parent.expanded = !parent.expanded
            }
        }

        /* factual fields — only real projected fields render */
        Flow {
            Layout.fillWidth: true
            spacing: MichiSpacing.md
            visible: root.hasFactualFields()

            function hasFactualFields() {
                return (root.knowledge.country || "")
                        + (root.knowledge.area || "")
                        + root.knowledge.beginYear
                        + (root.knowledge.artistType || "")
                        + (root.knowledge.website || "")
                        + (root.knowledge.label || "")
                        + root.knowledge.releaseYear
                        + (root.knowledge.genres || []).length
                    > 0
            }

            function fact(label, value) {
                if (typeof value === "string" && value.length === 0)
                    return null
                if (typeof value === "number" && value === 0)
                    return null
                return { label: label, value: value }
            }

            Repeater {
                model: [
                    root.fact("Country", root.knowledge.country),
                    root.fact("Area", root.knowledge.area),
                    root.fact("Active from", root.knowledge.beginYear),
                    root.fact("Active until", root.knowledge.endYear),
                    root.fact("Type", root.knowledge.artistType),
                    root.fact("Website", root.knowledge.website),
                    root.fact("Label", root.knowledge.label),
                    root.fact("Release year", root.knowledge.releaseYear),
                    root.fact("Genres", root.knowledge.genres
                              ? root.knowledge.genres.join(", ") : ""),
                ]
                delegate: Item {
                    required property var modelData
                    visible: modelData !== null
                    width: Math.min(240, factRow.implicitWidth + MichiSpacing.md)
                    height: factRow.implicitHeight + MichiSpacing.sm

                    ColumnLayout {
                        id: factRow
                        anchors.fill: parent
                        anchors.margins: MichiSpacing.sm
                        spacing: 2
                        MichiText {
                            text: modelData ? modelData.label : ""
                            role: "caption"
                            color: MichiPalette.textMuted
                        }
                        MichiText {
                            text: modelData ? String(modelData.value) : ""
                            role: "body"
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        EnrichmentAttribution {
            sources: root.sources
        }
    }

    /* empty surface: keep layout quiet — the view decides whether to
     * show a CTA via EnrichmentActions */
    onHasKnowledgeChanged: root.visible = root.hasKnowledge
}
