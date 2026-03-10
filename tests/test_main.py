import pytest
from main import StreamConfig


class TestStreamConfig:
    """Test StreamConfig dataclass and FFmpeg command generation"""

    def test_default_config(self):
        """Test default configuration values"""
        config = StreamConfig()
        assert config.video_device == "/dev/video0"
        assert config.video_format == "yuyv422"
        assert config.resolution == (640, 480)
        assert config.frame_rate == 30
        assert config.audio_enabled is False
        assert config.audio_device is None

    def test_custom_video_config(self):
        """Test custom video configuration"""
        config = StreamConfig(
            video_device="/dev/video1",
            video_format="mjpeg",
            resolution=(1280, 720),
            frame_rate=60
        )
        assert config.video_device == "/dev/video1"
        assert config.video_format == "mjpeg"
        assert config.resolution == (1280, 720)
        assert config.frame_rate == 60

    def test_audio_enabled_config(self):
        """Test configuration with audio enabled"""
        config = StreamConfig(
            audio_enabled=True,
            audio_device="hw:0,0",
            audio_sample_rate=48000,
            audio_channels=2
        )
        assert config.audio_enabled is True
        assert config.audio_device == "hw:0,0"
        assert config.audio_sample_rate == 48000
        assert config.audio_channels == 2

    def test_to_ffmpeg_video_args_default(self):
        """Test FFmpeg video arguments generation with default config"""
        config = StreamConfig()
        args = config.to_ffmpeg_video_args()

        assert "ffmpeg" in args
        assert "-f" in args
        assert "v4l2" in args
        assert "-input_format" in args
        assert "yuyv422" in args
        assert "-framerate" in args
        assert "30" in args
        assert "-video_size" in args
        assert "640x480" in args
        assert "-i" in args
        assert "/dev/video0" in args
        assert "mjpeg" in args
        assert "pipe:1" in args

    def test_to_ffmpeg_video_args_custom(self):
        """Test FFmpeg video arguments generation with custom config"""
        config = StreamConfig(
            video_device="/dev/video2",
            video_format="mjpeg",
            resolution=(1920, 1080),
            frame_rate=24
        )
        args = config.to_ffmpeg_video_args()

        assert "/dev/video2" in args
        assert "mjpeg" in args
        assert "1920x1080" in args
        assert "24" in args

    def test_to_ffmpeg_audio_args_disabled(self):
        """Test FFmpeg audio arguments when audio is disabled"""
        config = StreamConfig(audio_enabled=False)
        args = config.to_ffmpeg_audio_args()
        assert args == []

    def test_to_ffmpeg_audio_args_no_device(self):
        """Test FFmpeg audio arguments when audio enabled but no device"""
        config = StreamConfig(audio_enabled=True, audio_device=None)
        args = config.to_ffmpeg_audio_args()
        assert args == []

    def test_to_ffmpeg_audio_args_enabled(self):
        """Test FFmpeg audio arguments when audio is enabled"""
        config = StreamConfig(
            audio_enabled=True,
            audio_device="hw:1,0",
            audio_sample_rate=48000,
            audio_channels=2
        )
        args = config.to_ffmpeg_audio_args()

        assert "ffmpeg" in args
        assert "-f" in args
        assert "alsa" in args
        assert "-i" in args
        assert "hw:1,0" in args
        assert "-ar" in args
        assert "48000" in args
        assert "-ac" in args
        assert "2" in args
        assert "s16le" in args
        assert "pipe:1" in args

    def test_resolution_tuple_format(self):
        """Test that resolution is properly formatted in FFmpeg args"""
        config = StreamConfig(resolution=(800, 600))
        args = config.to_ffmpeg_video_args()
        assert "800x600" in args

    def test_frame_rate_string_conversion(self):
        """Test that frame rate is converted to string in FFmpeg args"""
        config = StreamConfig(frame_rate=15)
        args = config.to_ffmpeg_video_args()
        assert "15" in args
        assert isinstance(args[args.index("-framerate") + 1], str)

    def test_audio_sample_rate_string_conversion(self):
        """Test that audio sample rate is converted to string"""
        config = StreamConfig(
            audio_enabled=True,
            audio_device="hw:0,0",
            audio_sample_rate=44100
        )
        args = config.to_ffmpeg_audio_args()
        assert "44100" in args
        assert isinstance(args[args.index("-ar") + 1], str)


class TestRestAPIEndpoints:
    """Test REST API endpoints for device detection and stream control"""

    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app"""
        from main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_devices(self, monkeypatch):
        """Mock device detection functions"""
        def mock_detect_video():
            return [
                {
                    'device_path': '/dev/video0',
                    'device_name': 'Test Webcam',
                    'device_type': 'video',
                    'capabilities': {
                        'formats': ['yuyv422', 'mjpeg'],
                        'resolutions': [[640, 480], [1280, 720]],
                        'frame_rates': [15, 30]
                    }
                }
            ]

        def mock_detect_audio():
            return [
                {
                    'device_path': 'hw:0,0',
                    'device_name': 'Test Microphone',
                    'device_type': 'audio',
                    'capabilities': {
                        'formats': ['S16_LE'],
                        'sample_rates': [44100, 48000],
                        'channels': [1, 2]
                    }
                }
            ]

        import device_detector
        monkeypatch.setattr(device_detector, 'detect_video_devices', mock_detect_video)
        monkeypatch.setattr(device_detector, 'detect_audio_devices', mock_detect_audio)

    def test_get_devices_success(self, client, mock_devices):
        """Test GET /api/devices returns both video and audio devices"""
        response = client.get('/api/devices')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert 'video_devices' in data
        assert 'audio_devices' in data
        assert len(data['video_devices']) == 1
        assert len(data['audio_devices']) == 1
        assert data['video_devices'][0]['device_path'] == '/dev/video0'
        assert data['audio_devices'][0]['device_path'] == 'hw:0,0'

    def test_get_devices_empty(self, client, monkeypatch):
        """Test GET /api/devices when no devices are found"""
        import device_detector
        monkeypatch.setattr(device_detector, 'detect_video_devices', lambda: [])
        monkeypatch.setattr(device_detector, 'detect_audio_devices', lambda: [])

        response = client.get('/api/devices')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert data['video_devices'] == []
        assert data['audio_devices'] == []

    def test_stream_start_missing_video_device(self, client):
        """Test POST /api/stream/start without video_device"""
        response = client.post('/api/stream/start',
                               json={},
                               content_type='application/json')
        assert response.status_code == 400

        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'MISSING_VIDEO_DEVICE'

    def test_stream_start_invalid_json(self, client):
        """Test POST /api/stream/start with invalid JSON"""
        response = client.post('/api/stream/start',
                               data='not json',
                               content_type='application/json')
        assert response.status_code == 400

        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_REQUEST'

    def test_stream_start_invalid_resolution(self, client, monkeypatch):
        """Test POST /api/stream/start with invalid resolution"""
        # Mock subprocess to prevent actual FFmpeg execution
        import subprocess
        from unittest.mock import Mock
        monkeypatch.setattr(subprocess, 'Popen', Mock())

        response = client.post('/api/stream/start',
                               json={
                                   'video_device': '/dev/video0',
                                   'resolution': [-1, 480]
                               },
                               content_type='application/json')
        assert response.status_code == 400

        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_RESOLUTION'

    def test_stream_start_invalid_frame_rate(self, client, monkeypatch):
        """Test POST /api/stream/start with invalid frame rate"""
        # Mock subprocess to prevent actual FFmpeg execution
        import subprocess
        from unittest.mock import Mock
        monkeypatch.setattr(subprocess, 'Popen', Mock())

        response = client.post('/api/stream/start',
                               json={
                                   'video_device': '/dev/video0',
                                   'frame_rate': 0
                               },
                               content_type='application/json')
        assert response.status_code == 400

        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_FRAME_RATE'

    def test_stream_start_audio_enabled_no_device(self, client, monkeypatch):
        """Test POST /api/stream/start with audio enabled but no device"""
        # Mock subprocess to prevent actual FFmpeg execution
        import subprocess
        from unittest.mock import Mock
        monkeypatch.setattr(subprocess, 'Popen', Mock())

        response = client.post('/api/stream/start',
                               json={
                                   'video_device': '/dev/video0',
                                   'audio_enabled': True
                               },
                               content_type='application/json')
        assert response.status_code == 400

        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'MISSING_AUDIO_DEVICE'

    def test_stream_stop_success(self, client):
        """Test POST /api/stream/stop"""
        response = client.post('/api/stream/stop')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert 'message' in data

    def test_stream_status_stopped(self, client):
        """Test GET /api/stream/status when stream is stopped"""
        # First ensure stream is stopped
        client.post('/api/stream/stop')

        response = client.get('/api/stream/status')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert data['state'] == 'stopped'
        assert data['uptime_seconds'] == 0
        assert data['audio_active'] is False

    def test_stream_status_includes_config_when_running(self, client, monkeypatch):
        """Test GET /api/stream/status includes config when stream is running"""
        # Mock subprocess to prevent actual FFmpeg execution
        import subprocess
        from unittest.mock import Mock

        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: mock_process)

        # Start a stream
        client.post('/api/stream/start',
                    json={
                        'video_device': '/dev/video0',
                        'resolution': [640, 480],
                        'frame_rate': 30
                    },
                    content_type='application/json')

        # Check status
        response = client.get('/api/stream/status')
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert data['state'] == 'running'
        assert 'config' in data
        assert data['config']['video_device'] == '/dev/video0'
        assert data['config']['resolution'] == [640, 480]
        assert data['config']['frame_rate'] == 30

    def test_video_feed_endpoint_exists(self, client, monkeypatch):
        """Test that /video_feed endpoint exists"""
        # Mock subprocess to prevent actual FFmpeg execution
        import subprocess
        from unittest.mock import Mock

        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.read = Mock(return_value=b'')  # Return empty to end the generator
        monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: mock_process)

        response = client.get('/video_feed')
        # The endpoint exists (not 404)
        assert response.status_code == 200

    def test_audio_feed_endpoint_exists(self, client):
        """Test that /audio_feed endpoint exists"""
        response = client.get('/audio_feed')
        # Should return 400 when audio is not enabled
        assert response.status_code == 400

    def test_index_endpoint(self, client):
        """Test that / endpoint returns HTML"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Webcam Streamer' in response.data
        # Verify key UI elements are present
        assert b'videoDevice' in response.data
        assert b'audioDevice' in response.data
        assert b'resolution' in response.data
        assert b'Start Stream' in response.data
        assert b'Stop Stream' in response.data


class TestErrorHandling:
    """Test error handling features (Requirements 6.1-6.5)"""

    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app"""
        from main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_ffmpeg_not_found_error(self, client, monkeypatch):
        """Test error handling when FFmpeg is not found (Requirement 6.4)"""
        import subprocess
        import main

        # Ensure stream is stopped first
        main.stream_state = main.StreamState.STOPPED
        main.video_process = None
        main.audio_process = None

        def mock_popen(*args, **kwargs):
            raise FileNotFoundError("ffmpeg not found")

        monkeypatch.setattr(subprocess, 'Popen', mock_popen)

        response = client.post('/api/stream/start',
                               json={'video_device': '/dev/video0'},
                               content_type='application/json')

        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'FFMPEG_NOT_FOUND'
        assert 'FFmpeg not found' in data['error']['message']
        assert 'suggestion' in data['error']
        assert 'install' in data['error']['suggestion'].lower()

    def test_video_start_failure_with_suggestion(self, client, monkeypatch):
        """Test error message includes actionable suggestion (Requirement 6.5)"""
        import subprocess
        import main

        # Ensure stream is stopped first
        main.stream_state = main.StreamState.STOPPED
        main.video_process = None
        main.audio_process = None

        def mock_popen(*args, **kwargs):
            raise Exception("Device not accessible")

        monkeypatch.setattr(subprocess, 'Popen', mock_popen)

        response = client.post('/api/stream/start',
                               json={'video_device': '/dev/video0'},
                               content_type='application/json')

        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'suggestion' in data['error']
        assert len(data['error']['suggestion']) > 0

    def test_audio_failure_continues_video(self, client, monkeypatch):
        """Test that audio failure doesn't stop video stream (Requirement 6.2)"""
        import subprocess
        from unittest.mock import Mock
        import main

        # Ensure stream is stopped first
        main.stream_state = main.StreamState.STOPPED
        main.video_process = None
        main.audio_process = None

        call_count = [0]

        def mock_popen(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call is video - succeed
                mock_process = Mock()
                mock_process.stdout = Mock()
                mock_process.stderr = Mock()
                return mock_process
            else:
                # Second call is audio - fail
                raise Exception("Audio device not found")

        monkeypatch.setattr(subprocess, 'Popen', mock_popen)

        response = client.post('/api/stream/start',
                               json={
                                   'video_device': '/dev/video0',
                                   'audio_enabled': True,
                                   'audio_device': 'hw:0,0'
                               },
                               content_type='application/json')

        # Should succeed despite audio failure
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Audio should be disabled in the returned config
        assert data['config']['audio_enabled'] is False

    def test_device_detection_error_handling(self, client, monkeypatch):
        """Test device detection error is handled gracefully (Requirement 6.3)"""
        import device_detector

        def mock_detect_video():
            raise Exception("Device enumeration failed")

        monkeypatch.setattr(device_detector, 'detect_video_devices', mock_detect_video)
        monkeypatch.setattr(device_detector, 'detect_audio_devices', lambda: [])

        response = client.get('/api/devices')

        # Should return error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert data['error']['code'] == 'DEVICE_DETECTION_ERROR'

    def test_stream_stop_with_timeout(self, client, monkeypatch):
        """Test stream stop handles process timeout gracefully"""
        import subprocess
        from unittest.mock import Mock

        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock(side_effect=subprocess.TimeoutExpired('cmd', 5))
        mock_process.kill = Mock()

        # Set up a running stream
        import main
        main.video_process = mock_process
        main.stream_state = main.StreamState.RUNNING

        response = client.post('/api/stream/stop')

        # Should succeed with forced termination
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'forced' in data['message'].lower() or 'stopped' in data['message'].lower()

        # Verify kill was called
        mock_process.kill.assert_called_once()

    def test_error_messages_are_structured(self, client, monkeypatch):
        """Test that all error responses follow the structured format (Requirement 6.5)"""
        import subprocess

        def mock_popen(*args, **kwargs):
            raise Exception("Test error")

        monkeypatch.setattr(subprocess, 'Popen', mock_popen)

        response = client.post('/api/stream/start',
                               json={'video_device': '/dev/video0'},
                               content_type='application/json')

        data = response.get_json()
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
        assert 'details' in data['error']
        # Verify error structure is complete
        assert isinstance(data['error']['code'], str)
        assert isinstance(data['error']['message'], str)
        assert len(data['error']['message']) > 0
