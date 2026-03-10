# Installation Guide

## Quick Start (Raspberry Pi)

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv python3-pyaudio v4l-utils alsa-utils
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python main.py
```

The application will start on `http://0.0.0.0:8080`

## Detailed Installation

### Video Support (Required)

OpenCV is required for video streaming:

```bash
# Option 1: System package (recommended for Raspberry Pi)
sudo apt-get install python3-opencv

# Option 2: Via pip
pip install opencv-python
```

### Audio Support (Optional)

PyAudio is optional. The application will work in video-only mode without it.

```bash
# Option 1: System package (recommended for Raspberry Pi)
sudo apt-get install python3-pyaudio

# Option 2: Via pip (requires build dependencies)
sudo apt-get install python3-dev portaudio19-dev
pip install pyaudio
```

### Device Detection Tools

For automatic device detection:

```bash
sudo apt-get install v4l-utils alsa-utils
```

## Troubleshooting

### PyAudio Installation Fails

If you get compilation errors with PyAudio:

1. Use the system package instead:
   ```bash
   sudo apt-get install python3-pyaudio
   ```

2. Or skip audio support - the app works fine with video only

### ALSA Warnings

ALSA warnings like "Unknown PCM" are normal and can be ignored. They appear when PyAudio probes for available audio devices.

### Video Device Not Found

Check available video devices:
```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

### Audio Device Not Found

Check available audio devices:
```bash
arecord -l
```

## Virtual Environment (Optional)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Note: If using a virtual environment, you may need to install system packages globally or use `--system-site-packages` when creating the venv.

## Testing Installation

```bash
# Test video capture
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"

# Test audio (if installed)
python3 -c "import pyaudio; print('PyAudio available')"

# Run tests
pytest tests/ -v
```
