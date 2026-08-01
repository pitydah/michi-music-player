import QtQuick

// FocusTrap — keeps keyboard focus cycling inside a dialog while it is open.
//
// Usage:
//   FocusTrap {
//       container: dialogFrame
//       items: [field, cancelButton, confirmButton]
//       active: dialog.open
//   }
//
// If `items` is empty the trap collects every descendant of `container`
// with activeFocusOnTab === true, in visual order.
QtObject {
    id: trap

    property Item container: null
    property bool active: false
    property list<Item> items: []

    function focusableItems() {
        if (trap.items.length > 0)
            return trap.items.filter(function (item) {
                return item && item.visible !== false && item.enabled !== false
            })
        var found = []
        if (trap.container)
            _collect(trap.container, found)
        return found
    }

    function _collect(item, found) {
        var children = item.children || []
        for (var i = 0; i < children.length; i++) {
            var child = children[i]
            if (child.activeFocusOnTab === true && child.visible !== false && child.enabled !== false)
                found.push(child)
            _collect(child, found)
        }
    }

    function focusFirst() {
        var chain = focusableItems()
        if (chain.length > 0)
            chain[0].forceActiveFocus()
    }

    function focusLast() {
        var chain = focusableItems()
        if (chain.length > 0)
            chain[chain.length - 1].forceActiveFocus()
    }

    function cycleForward() {
        var chain = focusableItems()
        if (chain.length === 0)
            return
        var current = _currentIndex(chain)
        var next = current < 0 ? 0 : (current + 1) % chain.length
        chain[next].forceActiveFocus()
    }

    function cycleBackward() {
        var chain = focusableItems()
        if (chain.length === 0)
            return
        var current = _currentIndex(chain)
        var prev = current < 0 ? chain.length - 1 : (current - 1 + chain.length) % chain.length
        chain[prev].forceActiveFocus()
    }

    function _currentIndex(chain) {
        var win = trap.container ? trap.container.Window.window : null
        var focused = win ? win.activeFocusItem : null
        for (var i = 0; i < chain.length; i++) {
            if (chain[i] === focused || (chain[i].activeFocus === true))
                return i
        }
        return -1
    }
}
