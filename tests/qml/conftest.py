"""pytest plugin: extracts qml_module, qml_dimension, qml_workflow markers as JUnit user_properties."""


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        for marker_name in ("qml_module", "qml_dimension", "qml_workflow", "qml_route", "qml_widget_replacement"):
            marker = item.get_closest_marker(marker_name)
            if marker and marker.args:
                item.user_properties.append((marker_name, str(marker.args[0])))
        # Also check class-level markers
        if hasattr(item, 'parent') and hasattr(item.parent, 'obj'):
            parent = item.parent.obj
            if hasattr(parent, 'pytestmark'):
                for pm in parent.pytestmark:
                    if pm.name in ("qml_module", "qml_dimension", "qml_workflow", "qml_route", "qml_widget_replacement") and pm.args:
                        item.user_properties.append((pm.name, str(pm.args[0])))
