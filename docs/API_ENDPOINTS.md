# REST API Endpoints Documentation

This document describes the REST API endpoints added to the webcam streamer application.

## Base URL

```
http://localhost:8080
```

## Endpoints

### 1. GET /api/devices

Get all available video and audio devices.

**Response:**
```json
{
  "success": true,
  "video_devices": [
    {
      "device_path": "/dev/video0",
      "device_name": "HD Pro Webcam C920",
      "device_type": "video",
      "capabilities": {
        "formats": ["yuyv422", "mjpeg"],
        "resolutions": [[640, 480], [1280, 720]],
        "frame_rates": [15, 30, 60]
      }
    }
  ],
  "audio_devices": [
    {
      "device_path": "hw:0,0",
      "device_name": "USB Audio Device",
      "device_type": "audio",
      "capabilities": {
        "formats": ["S16_LE", "S32_LE"],
        "sample_rates": [44100, 48000],
        "channels": [1, 2]
      }
    }
  ]
}
```

### 2. POST /api/stream/start

Start video and optional audio streams with the provided configuration.

**Request Body:**
```json
{
  "video_device": "/dev/video0",
  "video_format": "yuyv422",
  "resolution": [640, 480],
  "frame_rate": 30,
  "audio_enabled": false,
  "audio_device": null,
  "audio_format": "s16le",
  "audio_sample_rate": 44100,
  "audio_channels": 1
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Stream started successfully",
  "config": {
    "video_device": "/dev/video0",
    "video_format": "yuyv422",
    "resolution": [640, 480],
    "frame_rate": 30,
    "audio_enabled": false,
    "audio_device": null
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "MISSING_VIDEO_DEVICE",
    "message": "video_device is required",
    "suggestion": "Specify a video device path (e.g., /dev/video0)"
  }
}
```

**Error Codes:**
- `STREAM_ALREADY_RUNNING` - Stream is already running
- `INVALID_REQUEST` - Request body is not valid JSON
- `MISSING_VIDEO_DEVICE` - video_device field is required
- `INVALID_RESOLUTION` - Resolution dimensions must be positive
- `INVALID_FRAME_RATE` - Frame rate must be positive
- `MISSING_AUDIO_DEVICE` - Audio enabled but no device specified
- `VIDEO_START_FAILED` - Failed to start video stream
- `STREAM_START_ERROR` - General stream start error

### 3. POST /api/stream/stop

Stop all active streams (video and audio).

**Response:**
```json
{
  "success": true,
  "message": "Stream stopped successfully"
}
```

### 4. GET /api/stream/status

Get current stream status including state, configuration, and statistics.

**Response (Stream Running):**
```json
{
  "success": true,
  "state": "running",
  "uptime_seconds": 45.2,
  "audio_active": false,
  "error_message": null,
  "config": {
    "video_device": "/dev/video0",
    "video_format": "yuyv422",
    "resolution": [640, 480],
    "frame_rate": 30,
    "audio_enabled": false,
    "audio_device": null,
    "audio_format": "s16le",
    "audio_sample_rate": 44100,
    "audio_channels": 1
  }
}
```

**Response (Stream Stopped):**
```json
{
  "success": true,
  "state": "stopped",
  "uptime_seconds": 0,
  "audio_active": false,
  "error_message": null
}
```

**Stream States:**
- `stopped` - No stream is running
- `starting` - Stream is being initialized
- `running` - Stream is active
- `error` - Stream encountered an error

### 5. GET /video_feed

Stream MJPEG video frames (existing endpoint, maintained).

**Response:** Multipart MJPEG stream

### 6. GET /audio_feed

Stream audio data (existing endpoint, maintained).

**Response:** Raw audio stream or 400 error if audio not enabled

## Example Usage

### Python with requests

```python
import requests

# Get available devices
response = requests.get('http://localhost:8080/api/devices')
devices = response.json()

# Start stream
config = {
    'video_device': '/dev/video0',
    'resolution': [640, 480],
    'frame_rate': 30
}
response = requests.post('http://localhost:8080/api/stream/start', json=config)

# Check status
response = requests.get('http://localhost:8080/api/stream/status')
status = response.json()

# Stop stream
response = requests.post('http://localhost:8080/api/stream/stop')
```

### JavaScript with fetch

```javascript
// Get available devices
fetch('http://localhost:8080/api/devices')
  .then(response => response.json())
  .then(data => console.log(data));

// Start stream
fetch('http://localhost:8080/api/stream/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_device: '/dev/video0',
    resolution: [640, 480],
    frame_rate: 30
  })
})
  .then(response => response.json())
  .then(data => console.log(data));

// Stop stream
fetch('http://localhost:8080/api/stream/stop', { method: 'POST' })
  .then(response => response.json())
  .then(data => console.log(data));
```

## Requirements Mapping

This implementation satisfies the following requirements:

- **Requirement 1.5**: Device enumeration API (GET /api/devices)
- **Requirement 2.1**: Audio device detection (GET /api/devices)
- **Requirement 3.4**: Audio streaming endpoint (GET /audio_feed)
- **Requirement 4.1**: Device list display (GET /api/devices)
- **Requirement 4.2**: Device selection (POST /api/stream/start)
- **Requirement 4.6**: Streaming status display (GET /api/stream/status)
- **Requirement 8.1**: Real-time streaming status (GET /api/stream/status)
