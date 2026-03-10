# Device Detector Module

## Overview

The `device_detector.py` module provides automatic detection of video and audio devices on Linux systems. It uses `v4l2-ctl` for video device enumeration and `arecord` for audio device detection.

## Features

- **Video Device Detection**: Enumerates all V4L2 video devices (webcams)
- **Audio Device Detection**: Enumerates all ALSA/PulseAudio input devices (microphones)
- **Capability Querying**: Retrieves supported formats, resolutions, frame rates, and sample rates
- **JSON Serialization**: Returns simple dictionaries that can be easily serialized to JSON
- **Error Handling**: Gracefully handles missing tools, device access errors, and parsing failures

## Requirements

### System Dependencies

- **v4l-utils**: Required for video device detection
  ```bash
  # Debian/Ubuntu
  sudo apt-get install v4l-utils

  # Fedora/RHEL
  sudo dnf install v4l-utils
  ```

- **alsa-utils**: Required for audio device detection
  ```bash
  # Debian/Ubuntu
  sudo apt-get install alsa-utils

  # Fedora/RHEL
  sudo dnf install alsa-utils
  ```

### Python Dependencies

- Python 3.7+
- No additional Python packages required (uses only standard library)

## Usage

### Detecting Video Devices

```python
import device_detector

# Get all video devices
video_devices = device_detector.detect_video_devices()

for device in video_devices:
    print(f"Device: {device['device_name']}")
    print(f"Path: {device['device_path']}")
    print(f"Formats: {device['capabilities']['formats']}")
    print(f"Resolutions: {device['capabilities']['resolutions']}")
    print(f"Frame rates: {device['capabilities']['frame_rates']}")
```

### Detecting Audio Devices

```python
import device_detector

# Get all audio devices
audio_devices = device_detector.detect_audio_devices()

for device in audio_devices:
    print(f"Device: {device['device_name']}")
    print(f"Path: {device['device_path']}")
    print(f"Formats: {device['capabilities']['formats']}")
    print(f"Sample rates: {device['capabilities']['sample_rates']}")
    print(f"Channels: {device['capabilities']['channels']}")
```

### Querying Specific Device Capabilities

```python
import device_detector

# Query capabilities for a specific video device
caps = device_detector.get_video_capabilities('/dev/video0')
if caps:
    print(f"Formats: {caps['formats']}")
    print(f"Resolutions: {caps['resolutions']}")
    print(f"Frame rates: {caps['frame_rates']}")

# Query capabilities for a specific audio device
caps = device_detector.get_audio_capabilities('hw:0,0')
if caps:
    print(f"Formats: {caps['formats']}")
    print(f"Sample rates: {caps['sample_rates']}")
    print(f"Channels: {caps['channels']}")
```

## Data Structures

### Video Device Info

```python
{
    'device_path': '/dev/video0',
    'device_name': 'HD Pro Webcam C920',
    'device_type': 'video',
    'capabilities': {
        'formats': ['yuyv', 'mjpeg'],
        'resolutions': [(640, 480), (1280, 720), (1920, 1080)],
        'frame_rates': [15, 30, 60]
    }
}
```

### Audio Device Info

```python
{
    'device_path': 'hw:0,0',
    'device_name': 'USB Audio Device',
    'device_type': 'audio',
    'capabilities': {
        'formats': ['S16_LE', 'S32_LE'],
        'sample_rates': [44100, 48000],
        'channels': [1, 2]
    }
}
```

## Error Handling

The module handles various error conditions gracefully:

- **Missing Tools**: If `v4l2-ctl` or `arecord` are not installed, functions return empty lists and log errors
- **Device Access Errors**: If a device cannot be accessed, it is excluded from the results
- **Parsing Errors**: If device output cannot be parsed, the device is skipped with a warning
- **Timeouts**: Commands that take too long are terminated, and the error is logged

All errors are logged using Python's `logging` module at appropriate levels (ERROR, WARNING).

## Testing

### Unit Tests

Run the unit tests with pytest:

```bash
pytest test_device_detector.py -v
```

The unit tests use mocking to simulate device detection without requiring actual hardware.

### Manual Testing

Run the manual test script on a system with actual devices:

```bash
python test_manual_device_detection.py
```

This will detect and display all available video and audio devices on your system.

## Implementation Notes

### Video Device Detection

- Uses `v4l2-ctl --list-devices` to enumerate devices
- Uses `v4l2-ctl --device=/dev/videoX --list-formats-ext` to query capabilities
- Parses output using regular expressions to extract device names, paths, and capabilities
- Handles multiple devices per physical camera (e.g., /dev/video0 and /dev/video1)

### Audio Device Detection

- Uses `arecord -l` to enumerate ALSA capture devices
- Parses card and device numbers to construct ALSA device identifiers (hw:X,Y)
- Returns common default capabilities (S16_LE, S32_LE formats at 44100/48000 Hz)
- Tests device accessibility with a zero-duration recording attempt

### Capability Parsing

- Video formats are normalized to lowercase (e.g., 'YUYV' → 'yuyv')
- Resolutions are stored as tuples of (width, height)
- Frame rates are rounded to integers
- Results are sorted for consistent ordering

## Requirements Validation

This module satisfies the following requirements from the specification:

- **Requirement 1.1**: Enumerates all available webcam devices on system startup
- **Requirement 1.2**: Retrieves supported formats, resolutions, and frame rates
- **Requirement 1.4**: Identifies each device by system path and human-readable name
- **Requirement 2.1**: Enumerates all available microphone devices
- **Requirement 2.2**: Identifies each microphone by system identifier and name
- **Requirement 2.4**: Retrieves supported audio formats and sample rates

## Future Enhancements

Potential improvements for future versions:

- Cache device information with TTL to reduce system calls
- Support for device hotplug detection (udev integration)
- More detailed audio capability querying (actual format support testing)
- Support for additional video backends (GStreamer, DirectShow on Windows)
- Asynchronous device detection for better performance
