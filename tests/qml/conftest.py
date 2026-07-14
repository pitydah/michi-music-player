def pytest_configure(config):
    config.addinivalue_line("markers", "qml_module(name): mark test as belonging to a QML module")
    config.addinivalue_line("markers", "qml_dimension(name): mark test as covering a QML dimension")
    config.addinivalue_line("markers", "qml_route(name): mark test as covering a QML route")
    config.addinivalue_line("markers", "qml_workflow(name): mark test as covering a QML workflow")
    config.addinivalue_line("markers", "widget_replacement(name): mark test as covering a widget replacement")
