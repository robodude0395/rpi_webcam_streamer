# Technology Stack

## Core Technologies

- Python 3.7+
- Flask (web framework)
- Flask-SocketIO (WebSocket support for real-time audio streaming)
- gevent (async I/O for WebSocket)
- OpenCV (cv2) - Video capture and processing
- PyAudio - Real-time audio capture

## System Dependencies

- v4l-utils (video device detection via v4l2-ctl)
- alsa-utils (audio device detection via arecord)
- python3-opencv (video capture)
- python3-pyaudio (audio capture)
- Linux with V4L2 support

## Testing

- pytest (test framework)
- pytest-mock (mocking support)

## Common Commands

### Installation

```bash
# System dependencies (Debian/Ubuntu/Raspberry Pi OS)
sudo apt-get update
sudo apt-get install v4l-utils alsa-utils python3-opencv python3-pyaudio

# Python dependencies
pip install -r requirements.txt
```

### Running

```bash
# Start the application
python main.py

# Application runs on http://0.0.0.0:8080
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_main.py -v

# Run manual device detection test
python tests/test_manual_device_detection.py
```

## Architecture Notes

- Uses OpenCV for video capture (no FFmpeg subprocess overhead)
- Uses PyAudio callback mode for non-blocking audio capture
- Video streaming uses MJPEG over HTTP multipart response
- Audio streaming uses WebSocket (Socket.IO) with PCM data in real-time
- PyAudio callbacks send audio directly via WebSocket (no threading overhead)
- Web Audio API on client for low-latency playback
- Dataclass-based configuration (StreamConfig)
- Enum-based state management (StreamState)
- Optimized for Raspberry Pi efficiency (16kHz mono audio, configurable video quality)
