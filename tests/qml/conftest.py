def pytest_collection_modifyitems(session, config, items):
    for item in items:
        module = item.get_closest_marker("qml_module")
        dimension = item.get_closest_marker("qml_dimension")
        workflow = item.get_closest_marker("qml_workflow")
        route = item.get_closest_marker("qml_route")
        widget_replacement = item.get_closest_marker("qml_widget_replacement")
        if module:
            item.user_properties.append(("qml_module", module.args[0]))
        if dimension:
            item.user_properties.append(("qml_dimension", dimension.args[0]))
        if workflow:
            item.user_properties.append(("qml_workflow", workflow.args[0]))
        if route:
            item.user_properties.append(("qml_route", route.args[0]))
        if widget_replacement:
            item.user_properties.append(("qml_widget_replacement", widget_replacement.args[0]))
