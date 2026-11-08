import QtQuick
import QtQuick.Layouts

import "../theme"

ColumnLayout {
    id: root

    property var stages: []
    property string expandedStageId: ""
    property bool compact: false
    property bool configurationEnabled: !compact

    // Presentation models are stable while a stage keeps its identity. The
    // Repeater only rebuilds when a stage is added, removed or reordered.
    property var stageItems: []
    property var stageCache: ({})
    property bool stageSyncReady: false

    spacing: 0
    signal configurationRequested(string action)
    signal expansionRequested(string stageId)

    onStagesChanged: {
        if (root.stageSyncReady)
            root.syncStages()
    }

    function _stageValues(stage, index, count) {
        const item = stage || {}
        return {
            stageId: item.id === undefined ? String(index) : String(item.id),
            title: item.title || "",
            summary: item.summary || "",
            detail: item.detail || "",
            detailRows: item.detailRows || [],
            configAction: item.configAction || "NONE",
            stageState: item.state || "unknown",
            first: item.first !== undefined ? item.first : index === 0,
            last: item.last !== undefined ? item.last : index === count - 1,
            expandable: item.expandable !== undefined
                ? item.expandable : (item.detail || "").length > 0
        }
    }

    function _applyStageValues(data, values) {
        for (const key in values) {
            if (data[key] !== values[key])
                data[key] = values[key]
        }
    }

    function syncStages() {
        const incoming = root.stages || []
        const cache = root.stageCache
        const next = []
        const live = ({})
        let structureChanged = false

        for (let index = 0; index < incoming.length; index += 1) {
            const values = root._stageValues(incoming[index], index, incoming.length)
            live[values.stageId] = true
            let data = cache[values.stageId]
            if (!data) {
                data = stageDataComponent.createObject(root)
                if (!data)
                    continue
                cache[values.stageId] = data
                structureChanged = true
            }
            root._applyStageValues(data, values)
            next.push(data)
        }

        if (next.length !== root.stageItems.length)
            structureChanged = true
        if (!structureChanged) {
            for (let index = 0; index < next.length; index += 1) {
                if (next[index] !== root.stageItems[index]) {
                    structureChanged = true
                    break
                }
            }
        }

        const stale = []
        for (const key in cache) {
            if (!live[key]) {
                stale.push(cache[key])
                delete cache[key]
            }
        }

        if (structureChanged)
            root.stageItems = next
        for (let index = 0; index < stale.length; index += 1)
            stale[index].destroy()
    }

    Component {
        id: stageDataComponent
        MichiSignalStageData {}
    }

    Repeater {
        id: stageRepeater
        model: root.stageItems
        delegate: MichiSignalNode {
            required property var modelData
            required property int index

            objectName: "signalStage_" + modelData.stageId
            Layout.fillWidth: true
            stageIndex: index
            stageCount: root.stageItems.length
            compact: root.compact
            first: modelData.first
            last: modelData.last
            expanded: root.expandedStageId === modelData.stageId
            expandable: modelData.expandable
            iconName: modelData.stageId === "source" ? "file-music"
                : modelData.stageId === "decode" ? "binary"
                : modelData.stageId === "processing" ? "adjustments-horizontal"
                : modelData.stageId === "channel-remap" ? "arrows-exchange"
                : modelData.stageId === "output" ? "wave-sine"
                : "circuit-diode"
            title: modelData.title
            summary: modelData.summary
            detail: modelData.detail
            detailRows: modelData.detailRows
            configAction: root.configurationEnabled
                ? (modelData.configAction || "NONE") : "NONE"
            stageState: modelData.stageState
            onToggleRequested: {
                root.expansionRequested(root.expandedStageId === modelData.stageId
                    ? "" : modelData.stageId)
            }
            onConfigurationRequested: action => {
                root.configurationRequested(action)
            }
        }
    }

    function stageItem(stageId) {
        for (let index = 0; index < stageRepeater.count; index += 1) {
            const item = stageRepeater.itemAt(index)
            if (item && item.objectName === "signalStage_" + stageId)
                return item
        }
        return null
    }

    function focusFirstStage() {
        for (let index = 0; index < stageRepeater.count; index += 1) {
            const item = stageRepeater.itemAt(index)
            if (item && item.activeFocusOnTab) {
                item.forceActiveFocus()
                return
            }
        }
    }

    Component.onCompleted: {
        root.stageSyncReady = true
        root.syncStages()
    }
}
