# Audio Streaming Migration Notes

## Changes Made

The audio livestreaming system has been revamped to fix streaming issues while maintaining the same API structure and WebSocket architecture.

## Key Changes

### 1. Replaced FFmpeg with Native Libraries

**Before:**
- Used FFmpeg subprocess for video capture
- Used FFmpeg subprocess for audio capture
- Complex process management and error handling

**After:**
- OpenCV (cv2) for video capture - more reliable and direct
- PyAudio for audio capture - native Python audio interface (optional)
- Simpler error handling and resource management
- Graceful fallback to video-only mode if PyAudio unavailable

### 2. Video Streaming Improvements

- Direct frame capture using `cv2.VideoCapture()`
- JPEG encoding with `cv2.imencode()`
- Better frame rate control
- Automatic resolution adjustment
- More reliable device access

### 3. Audio Streaming Improvements

- PyAudio provides direct access to ALSA devices
- Simpler audio chunk reading with `stream.read()`
- WebSocket broadcasting maintained via Socket.IO
- Better error recovery for audio failures
- Non-blocking audio capture
- **Optional dependency** - app works without PyAudio in video-only mode

### 4. Configuration Updates

**New StreamConfig fields:**
- `video_device_index`: Integer index for OpenCV (e.g., 0, 1, 2)
- `audio_device_index`: Integer index for PyAudio
- Removed FFmpeg-specific format strings

**API remains backward compatible** - accepts both device paths and indices

### 5. Dependencies

**Required:**
```
opencv-python  # Video capture and processing
```

**Optional:**
```
pyaudio        # Audio capture (install via: sudo apt-get install python3-pyaudio)
```

## Benefits

1. **More Reliable**: Native libraries are more stable than subprocess management
2. **Better Performance**: Direct memory access, no pipe overhead
3. **Simpler Code**: Removed complex FFmpeg argument generation
4. **Easier Debugging**: Python exceptions instead of parsing FFmpeg stderr
5. **Flexible**: Works with or without audio support
6. **Raspberry Pi Optimized**: Uses system packages for better compatibility

## API Compatibility

All REST endpoints remain unchanged:
- `GET /api/devices` - Device enumeration (now includes `pyaudio_available` flag)
- `POST /api/stream/start` - Start streaming
- `POST /api/stream/stop` - Stop streaming
- `GET /api/stream/status` - Stream status (now includes `pyaudio_available` flag)
- `GET /video_feed` - Video MJPEG stream

WebSocket audio streaming via `/audio` namespace remains the same.

## Installation

### Quick Install (Recommended for Raspberry Pi)

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv python3-pyaudio v4l-utils alsa-utils

# Install Python dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Minimal Install (Video Only)

```bash
# Install only video support
sudo apt-get install python3-opencv
pip install flask flask-socketio python-socketio gevent gevent-websocket

# Run application (audio will be disabled)
python main.py
```

## Testing Recommendations

1. Test with different video device indices (0, 1, 2)
2. Test with different audio device indices
3. Verify WebSocket audio playback in browser
4. Test audio-only and video-only modes
5. Test device disconnection handling
6. Test graceful degradation when PyAudio is not installed

## Notes

- PyAudio is now optional - app runs in video-only mode without it
- ALSA warnings during startup are normal and can be ignored
- System packages (python3-pyaudio, python3-opencv) recommended for Raspberry Pi
- OpenCV provides better webcam support than V4L2 directly
- Audio still uses WebSocket (Socket.IO) as per architecture requirements
- Device detection module (device_detector.py) remains unchanged
