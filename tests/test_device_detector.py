"""
Unit tests for device_detector module.
"""

import pytest
from unittest.mock import patch, MagicMock
import device_detector


class TestVideoDeviceDetection:
    """Tests for video device detection functionality."""

    def test_detect_video_devices_success(self):
        """Test successful video device detection."""
        mock_list_output = """USB Camera (usb-0000:00:14.0-1):
\t/dev/video0
\t/dev/video1

Dummy video device (platform:v4l2loopback-000):
\t/dev/video2
"""

        mock_caps_output = """ioctl: VIDIOC_ENUM_FMT
\tType: Video Capture

\t[0]: 'YUYV' (YUYV 4:2:2)
\t\tSize: Discrete 640x480
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t\t\tInterval: Discrete 0.067s (15.000 fps)
\t\tSize: Discrete 1280x720
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t[1]: 'MJPG' (Motion-JPEG)
\t\tSize: Discrete 1920x1080
\t\t\tInterval: Discrete 0.033s (30.000 fps)
"""

        with patch('subprocess.run') as mock_run:
            # Mock the list-devices call
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_list_output,
                stderr=""
            )

            # Mock the list-formats-ext calls
            def side_effect(*args, **kwargs):
                if "--list-formats-ext" in args[0]:
                    return MagicMock(returncode=0, stdout=mock_caps_output, stderr="")
                return MagicMock(returncode=0, stdout=mock_list_output, stderr="")

            mock_run.side_effect = side_effect

            devices = device_detector.detect_video_devices()

            assert len(devices) == 3
            assert devices[0]['device_path'] == '/dev/video0'
            assert devices[0]['device_name'] == 'USB Camera'
            assert devices[0]['device_type'] == 'video'
            assert 'capabilities' in devices[0]

    def test_detect_video_devices_no_devices(self):
        """Test when no video devices are found."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )

            devices = device_detector.detect_video_devices()
            assert devices == []

    def test_detect_video_devices_command_failure(self):
        """Test handling of v4l2-ctl command failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: command failed"
            )

            devices = device_detector.detect_video_devices()
            assert devices == []

    def test_detect_video_devices_v4l2ctl_not_found(self):
        """Test handling when v4l2-ctl is not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            devices = device_detector.detect_video_devices()
            assert devices == []


class TestVideoCapabilities:
    """Tests for video capability querying."""

    def test_get_video_capabilities_success(self):
        """Test successful capability query."""
        mock_output = """ioctl: VIDIOC_ENUM_FMT
\tType: Video Capture

\t[0]: 'YUYV' (YUYV 4:2:2)
\t\tSize: Discrete 640x480
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t\t\tInterval: Discrete 0.067s (15.000 fps)
\t\tSize: Discrete 1280x720
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t[1]: 'MJPG' (Motion-JPEG)
\t\tSize: Discrete 1920x1080
\t\t\tInterval: Discrete 0.033s (30.000 fps)
"""

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            caps = device_detector.get_video_capabilities('/dev/video0')

            assert caps is not None
            assert 'yuyv' in caps['formats']
            assert 'mjpg' in caps['formats']
            assert (640, 480) in caps['resolutions']
            assert (1280, 720) in caps['resolutions']
            assert (1920, 1080) in caps['resolutions']
            assert 15 in caps['frame_rates']
            assert 30 in caps['frame_rates']

    def test_get_video_capabilities_command_failure(self):
        """Test handling of capability query failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: device not found"
            )

            caps = device_detector.get_video_capabilities('/dev/video0')
            assert caps is None

    def test_get_video_capabilities_no_formats(self):
        """Test handling when no formats are found."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="No formats found",
                stderr=""
            )

            caps = device_detector.get_video_capabilities('/dev/video0')
            assert caps is None


class TestAudioDeviceDetection:
    """Tests for audio device detection functionality."""

    def test_detect_audio_devices_success(self):
        """Test successful audio device detection."""
        mock_output = """**** List of CAPTURE Hardware Devices ****
card 0: PCH [HDA Intel PCH], device 0: ALC887-VD Analog [ALC887-VD Analog]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""

        with patch('subprocess.run') as mock_run:
            def side_effect(*args, **kwargs):
                if args[0][0] == "arecord" and args[0][1] == "-l":
                    return MagicMock(returncode=0, stdout=mock_output, stderr="")
                # For capability test calls
                return MagicMock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = side_effect

            devices = device_detector.detect_audio_devices()

            assert len(devices) == 2
            assert devices[0]['device_path'] == 'hw:0,0'
            assert devices[0]['device_name'] == 'ALC887-VD Analog'
            assert devices[0]['device_type'] == 'audio'
            assert 'capabilities' in devices[0]

            assert devices[1]['device_path'] == 'hw:1,0'
            assert devices[1]['device_name'] == 'USB Audio'

    def test_detect_audio_devices_no_devices(self):
        """Test when no audio devices are found."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="**** List of CAPTURE Hardware Devices ****\n",
                stderr=""
            )

            devices = device_detector.detect_audio_devices()
            assert devices == []

    def test_detect_audio_devices_command_failure(self):
        """Test handling of arecord command failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: command failed"
            )

            devices = device_detector.detect_audio_devices()
            assert devices == []

    def test_detect_audio_devices_arecord_not_found(self):
        """Test handling when arecord is not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            devices = device_detector.detect_audio_devices()
            assert devices == []


class TestAudioCapabilities:
    """Tests for audio capability querying."""

    def test_get_audio_capabilities_success(self):
        """Test successful audio capability query."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )

            caps = device_detector.get_audio_capabilities('hw:0,0')

            assert caps is not None
            assert 'S16_LE' in caps['formats']
            assert 44100 in caps['sample_rates']
            assert 48000 in caps['sample_rates']
            assert 1 in caps['channels']
            assert 2 in caps['channels']

    def test_get_audio_capabilities_timeout(self):
        """Test handling of timeout during capability query."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = TimeoutError

            caps = device_detector.get_audio_capabilities('hw:0,0')
            # Should still return default capabilities on timeout
            assert caps is not None
            assert 'S16_LE' in caps['formats']

    def test_get_audio_capabilities_device_error(self):
        """Test handling of device access error."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Device access denied")

            caps = device_detector.get_audio_capabilities('hw:0,0')
            assert caps is None


class TestDeviceInfoStructure:
    """Tests for device info dictionary structure."""

    def test_video_device_has_required_fields(self):
        """Test that video device info has all required fields."""
        mock_list_output = "Test Camera:\n\t/dev/video0\n"
        mock_caps_output = "[0]: 'YUYV' (YUYV 4:2:2)\n\tSize: Discrete 640x480\n\t\tInterval: Discrete 0.033s (30.000 fps)\n"

        with patch('subprocess.run') as mock_run:
            def side_effect(*args, **kwargs):
                if "--list-formats-ext" in args[0]:
                    return MagicMock(returncode=0, stdout=mock_caps_output, stderr="")
                return MagicMock(returncode=0, stdout=mock_list_output, stderr="")

            mock_run.side_effect = side_effect

            devices = device_detector.detect_video_devices()

            assert len(devices) > 0
            device = devices[0]
            assert 'device_path' in device
            assert 'device_name' in device
            assert 'device_type' in device
            assert 'capabilities' in device
            assert device['device_path'] != ''
            assert device['device_name'] != ''
            assert device['device_type'] == 'video'

    def test_audio_device_has_required_fields(self):
        """Test that audio device info has all required fields."""
        mock_output = "card 0: Test [Test Audio], device 0: Test Device [Test Device]\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            devices = device_detector.detect_audio_devices()

            assert len(devices) > 0
            device = devices[0]
            assert 'device_path' in device
            assert 'device_name' in device
            assert 'device_type' in device
            assert 'capabilities' in device
            assert device['device_path'] != ''
            assert device['device_name'] != ''
            assert device['device_type'] == 'audio'
