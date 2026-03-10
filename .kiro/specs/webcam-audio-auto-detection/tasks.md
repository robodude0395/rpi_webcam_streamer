# Implementation Plan: Webcam Audio Auto-Detection

## Overview

This implementation plan focuses on simplicity and elegance. The core idea: extend the existing Flask app with device detection, make streams configurable, and add a clean web UI. Keep it minimal, keep it working.

## Tasks

- [x] 1. Add device detection
  - Create device_detector.py module with functions to detect video/audio devices using v4l2-ctl and arecord
  - Parse device names, paths, and basic capabilities (formats, resolutions, sample rates)
  - Return simple dictionaries for easy JSON serialization
  - _Requirements: 1.1, 1.2, 1.4, 2.1, 2.2, 2.4_

- [x] 2. Make streams configurable
  - Refactor main.py to accept device path, resolution, framerate as parameters
  - Add optional audio capture using FFmpeg (separate process if enabled)
  - Keep the existing MJPEG frame generation logic, just make it dynamic
  - _Requirements: 3.1, 3.2, 4.3, 5.2_

- [x] 3. Add REST API endpoints
  - GET /api/devices - return both video and audio devices in one call
  - POST /api/stream/start - accept config, start video (and optional audio) streams
  - POST /api/stream/stop - stop active streams
  - GET /api/stream/status - return current state and stats
  - Keep /video_feed and add /audio_feed endpoints
  - _Requirements: 1.5, 2.1, 3.4, 4.1, 4.2, 4.6, 8.1_

- [x] 4. Build simple web UI
  - Single HTML page with device dropdowns, resolution selector, audio toggle
  - Start/stop buttons and live status display
  - Embed video stream in <img> tag, audio in <audio> tag
  - Use vanilla JavaScript - no frameworks needed
  - _Requirements: 4.1, 4.2, 4.5, 5.1, 8.2, 8.6_

- [x] 5. Add basic error handling
  - Log errors clearly (device not found, FFmpeg failures, etc.)
  - Return helpful error messages in API responses
  - Handle stream failures gracefully (continue video if audio fails)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 6. Add stream recovery (optional)
  - Monitor FFmpeg process health
  - Auto-restart on failure (max 3 attempts with 2s delay)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

## Notes

- Focus on working code over perfect architecture
- Reuse existing FFmpeg streaming logic where possible
- Test manually with real webcam/microphone
- Property-based tests marked optional - add if time permits
- Keep everything in main.py and device_detector.py initially
- Can refactor later if needed
