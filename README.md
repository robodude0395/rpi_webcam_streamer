# Raspberry Pi Webcam Streamer

A Flask-based webcam and audio streaming application with automatic device detection, REST API, and web UI for Raspberry Pi and Linux systems.

## Features

- Automatic video and audio device detection
- Real-time MJPEG video streaming
- Audio streaming support
- REST API for device control
- Responsive web interface
- Configurable resolution and frame rate
- Stream status monitoring

## Quick Start

### Installation

1. Install system dependencies:
```bash
# Debian/Ubuntu/Raspberry Pi OS
sudo apt-get update
sudo apt-get install v4l-utils alsa-utils python3-pip
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python main.py
```

The application will start on `http://localhost:8080`

### Using the Web Interface

1. Open your browser to `http://localhost:8080`
2. Select a video device from the dropdown
3. Optionally enable audio and select a microphone
4. Choose resolution and frame rate
5. Click "Start Stream"

## Project Structure

```
.
├── main.py                 # Flask application and API endpoints
├── device_detector.py      # Device detection module
├── static/
│   └── index.html         # Web UI
├── tests/                 # Test files
│   ├── test_main.py
│   ├── test_device_detector.py
│   ├── test_api_manual.py
│   └── test_manual_device_detection.py
├── docs/                  # Documentation
│   ├── API_ENDPOINTS.md
│   ├── WEB_UI.md
│   └── DEVICE_DETECTOR.md
└── requirements.txt       # Python dependencies
```

## API Endpoints

- `GET /api/devices` - List all available video and audio devices
- `POST /api/stream/start` - Start streaming with configuration
- `POST /api/stream/stop` - Stop active streams
- `GET /api/stream/status` - Get current stream status
- `GET /video_feed` - MJPEG video stream
- `GET /audio_feed` - Audio stream

See [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md) for detailed API documentation.

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run manual device detection test:
```bash
python tests/test_manual_device_detection.py
```

## Documentation

- [API Endpoints](docs/API_ENDPOINTS.md) - REST API reference
- [Web UI](docs/WEB_UI.md) - Web interface documentation
- [Device Detector](docs/DEVICE_DETECTOR.md) - Device detection module details

## Requirements

- Python 3.7+
- Flask
- v4l-utils (for video device detection)
- alsa-utils (for audio device detection)
- Linux system with V4L2 support

## License

MIT
