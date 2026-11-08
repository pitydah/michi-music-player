"""Static wiring guards for the cumulative patch's Qt/QML boundary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_one_qt_owner_publishes_shared_read_model():
    bridge = ROOT / "src/michi/presentation/signal_truth_bridge.py"
    if not bridge.exists():
        # Pre-rename checkout candidate: the A41 migrator resolves this path.
        bridge = ROOT / "src/michi/presentation/signal_path_bridge.py"
    body = bridge.read_text(encoding="utf-8")
    assert body.count("self._publish_truth_frame()") == 2
    assert '@Property("QVariantMap", notify=state_changed)' in body
    assert "def truthFrame(self)" in body
    assert "publish_truth_frame(self._projection)" in body
    assert (
        "self._apply_output_owner_truth()\n            self._publish_truth_frame()"
        in body
    )


def test_popup_uses_read_model_for_proof_family_and_stages():
    qml = (ROOT / "src/michi/presentation/qml/player/SignalTruthPopup.qml").read_text()
    assert "readonly property var canonicalTruthFrame:" in qml
    assert "stages: root.canonicalTruthFrame.stages || []" in qml
    assert "readonly property string proofState:" in qml
    assert "canonicalTruthFrame.familyEvidenceState ||" in qml


def test_a42_no_second_recorder_or_qt_poller():
    text = (ROOT / "src/michi/application/signal_truth_frame.py").read_text()
    forbidden = (
        "SignalTruthRecorder(",
        "QTimer(",
        "QThread(",
        "subprocess.run(",
        "read_capture_state(",
        "OutputSessionService(",
    )
    assert all(token not in text for token in forbidden)
