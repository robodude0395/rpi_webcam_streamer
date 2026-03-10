# Product Overview

Raspberry Pi Webcam Streamer - A Flask-based application for real-time video and audio streaming with automatic device detection.

## Core Features

- Automatic detection of V4L2 video devices and ALSA audio devices
- Real-time MJPEG video streaming via HTTP
- Audio streaming via WebSocket (Socket.IO)
- REST API for device enumeration and stream control
- Responsive web interface for device selection and configuration
- Configurable resolution, frame rate, and audio settings
- Stream health monitoring with automatic error detection

## Target Platform

Designed for Raspberry Pi and Linux systems with V4L2 and ALSA support. Requires FFmpeg for media processing.

## Key Use Cases

- Remote webcam monitoring
- Audio/video capture for IoT projects
- Educational demonstrations of streaming protocols
- Device testing and capability discovery
