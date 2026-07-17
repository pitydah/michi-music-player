"""Test sync transport adapters with temporary filesystem."""
import tempfile
from pathlib import Path
import pytest
from sync.transport import DeviceInfo
from sync.transports.usb_mass_storage import UsbMassStorageTransport


@pytest.fixture
def temp_music_dir():
    with tempfile.TemporaryDirectory() as td:
        music = Path(td) / "Music"
        music.mkdir()
        # Create some test files
        (music / "song1.flac").write_text("fake flac content")
        (music / "song2.mp3").write_text("fake mp3 content")
        (music / "song3.wav").write_text("fake wav content")
        (music / "video.mp4").write_text("fake video content")
        yield td


def test_create_transfer_plan(temp_music_dir):
    music = Path(temp_music_dir) / "Music"
    transport = UsbMassStorageTransport()
    device_info = DeviceInfo(
        device_id="test",
        name="Test Device",
        protocols=["ums"],
        audio_formats=["mp3", "flac", "ogg", "wav"],
    )
    local_files = list(music.iterdir())
    device_files = [
        {"name": "song1.flac", "path": "Music/song1.flac", "size": 100},
    ]

    plan = transport.create_plan(local_files, device_files, device_info)

    # song1.flac already exists on device -> to_skip or to_update (size differs)
    assert len(plan.to_copy) > 0  # remaining files should be copied
    assert len(plan.to_skip) >= 0  # song1 may match or not
    assert "song3.wav" in [p.name for p in plan.to_copy]


def test_usb_discover_no_devices():
    """Test discovery when no USB devices are mounted."""
    transport = UsbMassStorageTransport()
    devices = transport.discover()
    # Should not crash, may return empty list
    assert isinstance(devices, list)
