# Web UI Documentation

## Overview

The webcam streamer now includes a simple, responsive web interface for controlling video and audio streams.

## Features

### Device Selection
- **Video Device Dropdown**: Select from all detected webcam devices
- **Audio Device Dropdown**: Select from all detected microphone devices
- **Audio Toggle**: Enable or disable audio streaming

### Stream Configuration
- **Resolution Selector**: Choose from common resolutions (640x480, 800x600, 1280x720, 1920x1080)
- **Frame Rate Selector**: Choose frame rate (15, 30, or 60 fps)

### Controls
- **Start Stream**: Begin video (and optional audio) streaming with selected configuration
- **Stop Stream**: Stop all active streams
- **Refresh Devices**: Re-scan system for connected devices

### Status Display
- Real-time stream status (Stopped, Starting, Running, Error)
- Current resolution and frame rate when streaming
- Stream uptime counter
- Active audio device information
- Error messages with helpful suggestions

### Stream Display
- **Video Stream**: Embedded in an `<img>` tag, updates in real-time
- **Audio Stream**: Embedded in an `<audio>` tag with playback controls (when enabled)

## Usage

1. **Start the Flask application**:
   ```bash
   python main.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:8080
   ```

3. **Select devices**:
   - Choose a video device from the dropdown
   - Optionally enable audio and select a microphone
   - Choose your desired resolution and frame rate

4. **Start streaming**:
   - Click "Start Stream"
   - The video will appear in the video container
   - If audio is enabled, the audio player will appear below

5. **Stop streaming**:
   - Click "Stop Stream" to end the stream

## Responsive Design

The UI is fully responsive and works on:
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Tablet devices
- Mobile phones

On smaller screens, the controls stack vertically for better usability.

## API Integration

The web UI communicates with the Flask backend using these REST API endpoints:

- `GET /api/devices` - Fetch available video and audio devices
- `POST /api/stream/start` - Start streaming with configuration
- `POST /api/stream/stop` - Stop active streams
- `GET /api/stream/status` - Get current stream status (polled every second)
- `GET /video_feed` - MJPEG video stream
- `GET /audio_feed` - Raw audio stream

## Technology Stack

- **HTML5**: Semantic markup
- **CSS3**: Modern styling with Grid and Flexbox layouts
- **Vanilla JavaScript**: No frameworks or dependencies
- **Fetch API**: For REST API communication

## Browser Compatibility

The UI uses modern web standards and is compatible with:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Error Handling

The UI displays user-friendly error messages for common issues:
- No devices found
- Device selection errors
- Stream start/stop failures
- Configuration validation errors

All errors include suggestions for resolution.
