# Project Structure

## Root Directory Layout

```
.
├── main.py                 # Flask application, API endpoints, streaming logic
├── device_detector.py      # Device detection module (V4L2 and ALSA)
├── simple_stream.py        # Simplified streaming example
├── requirements.txt        # Python dependencies
├── static/                 # Frontend assets
│   ├── index.html         # Web UI
│   └── audio_websocket.js # WebSocket audio client
├── tests/                 # Test suite
│   ├── test_main.py
│   ├── test_device_detector.py
│   ├── test_api_manual.py
│   └── test_manual_device_detection.py
└── docs/                  # Documentation
    ├── API_ENDPOINTS.md
    ├── WEB_UI.md
    └── DEVICE_DETECTOR.md
```

## Module Organization

### main.py
- Flask application setup and configuration
- REST API endpoints (/api/devices, /api/stream/start, /api/stream/stop, /api/stream/status)
- Stream endpoints (/video_feed for MJPEG, WebSocket /audio for real-time audio)
- StreamConfig dataclass for configuration management
- StreamState enum for state tracking
- PyAudio callback mode for efficient audio capture
- Socket.IO handlers for WebSocket audio streaming

### device_detector.py
- `detect_video_devices()` - Enumerate V4L2 video devices
- `get_video_capabilities()` - Query device formats, resolutions, frame rates
- `detect_audio_devices()` - Enumerate ALSA audio devices
- `get_audio_capabilities()` - Query audio formats and sample rates
- Returns simple dictionaries for JSON serialization

### static/
- Single-page web application
- Device selection dropdowns
- Stream configuration controls
- Real-time audio client using Web Audio API (embedded in index.html)

## Code Conventions

### Error Handling
- Structured error responses with code, message, details, and suggestion fields
- Non-fatal audio failures continue with video-only mode
- Stream health monitoring detects device disconnection
- Graceful degradation when system tools (v4l2-ctl, arecord) are missing

### Testing Patterns
- Pytest with fixtures for Flask test client
- Mock subprocess calls to prevent actual FFmpeg execution
- Monkeypatch for dependency injection
- Separate test classes for logical grouping (TestStreamConfig, TestRestAPIEndpoints, TestErrorHandling)

### Logging
- Standard Python logging module
- INFO level for normal operations
- WARNING for non-fatal issues (audio failures)
- ERROR for critical failures
- Structured log messages with context

### API Design
- RESTful endpoints with JSON request/response
- Consistent success/error response structure
- HTTP status codes: 200 (success), 400 (client error), 500 (server error)
- Descriptive error codes (MISSING_VIDEO_DEVICE, INVALID_RESOLUTION, etc.)
