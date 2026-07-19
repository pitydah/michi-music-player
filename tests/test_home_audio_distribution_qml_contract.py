from pathlib import Path


def test_distribution_page_uses_bridge_models_and_real_actions():
    qml = Path("ui_qml/pages/home_audio/DistributionHubPage.qml").read_text(
        encoding="utf-8"
    )

    for model in (
        "bridge.sources",
        "bridge.servers",
        "bridge.receiverList",
        "bridge.destinations",
        "bridge.routes",
    ):
        assert model in qml

    for action in (
        "startServer",
        "stopServer",
        "discoverReceivers",
        "createRoute",
        "startRoute",
        "stopRoute",
        "recoverRoute",
        "deleteRoute",
    ):
        assert action in qml

    assert 'navigationBridge.navigate("home_audio")' not in qml
