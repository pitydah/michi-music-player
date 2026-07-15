"""pytest configuration for QML tests — registers V9 markers and user_properties plugin."""


def pytest_configure(config):
    config.addinivalue_line("markers", "qml_module(name): mark test as belonging to a QML module")
    config.addinivalue_line("markers", "qml_dimension(name): mark test as covering a QML dimension")
    config.addinivalue_line("markers", "qml_route(name): mark test as covering a QML route")
    config.addinivalue_line("markers", "qml_workflow(name): mark test as covering a QML workflow")
    config.addinivalue_line("markers", "widget_replacement(name): mark test as covering a widget replacement")


def pytest_itemcollected(item):
    """Inject user_properties from markers for JUnit XML evidence collection."""
    markers = item.iter_markers()
    has_qml = False
    for marker in markers:
        if marker.name in ("qml_module", "qml_dimension", "qml_route"):
            has_qml = True
            break
    if has_qml:
        props = {}
        for marker in item.iter_markers():
            if marker.name == "qml_module":
                props["qml_module"] = marker.args[0] if marker.args else ""
            elif marker.name == "qml_dimension":
                val = marker.args[0] if marker.args else ""
                existing = props.get("qml_dimension", "")
                props["qml_dimension"] = f"{existing},{val}" if existing else val
            elif marker.name == "qml_route":
                props["qml_route"] = marker.args[0] if marker.args else ""
        item.user_properties = list(props.items())
