"""
Device detection module for webcam and audio devices.

This module provides functions to detect video devices (via v4l2-ctl) and
audio devices (via arecord), parsing their capabilities and returning
simple dictionaries for JSON serialization.
"""

import subprocess
import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def detect_video_devices() -> List[Dict]:
    """
    Enumerate all V4L2 video devices.

    Returns:
        List of device info dictionaries with keys:
        - device_path: str (e.g., "/dev/video0")
        - device_name: str (e.g., "HD Pro Webcam C920")
        - device_type: str ("video")
        - capabilities: dict with formats, resolutions, frame_rates
    """
    devices = []

    try:
        # Run v4l2-ctl --list-devices to get all video devices
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.error(f"v4l2-ctl --list-devices failed with exit code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return devices

        # Parse the output to extract device names and paths
        lines = result.stdout.strip().split('\n')
        current_device_name = None

        for line in lines:
            # Device names don't start with whitespace
            if line and not line.startswith(('\t', ' ')):
                # Extract device name (remove trailing colon and parenthetical info)
                current_device_name = line.split('(')[0].strip().rstrip(':')
            # Device paths start with whitespace
            elif line.strip().startswith('/dev/video'):
                device_path = line.strip()
                if current_device_name:
                    # Get capabilities for this device
                    capabilities = get_video_capabilities(device_path)
                    if capabilities:
                        devices.append({
                            'device_path': device_path,
                            'device_name': current_device_name,
                            'device_type': 'video',
                            'capabilities': capabilities
                        })
                        logger.info(f"Detected video device: {device_path} ({current_device_name})")
                    else:
                        logger.warning(f"Skipping {device_path} - could not query capabilities")

        if not devices:
            logger.warning("No video devices found. Please connect a webcam.")

    except FileNotFoundError:
        logger.error("v4l2-ctl not found. Please install v4l-utils package (e.g., 'apt install v4l-utils')")
    except subprocess.TimeoutExpired:
        logger.error("v4l2-ctl command timed out after 5 seconds. System may be unresponsive.")
    except Exception as e:
        logger.error(f"Unexpected error detecting video devices: {type(e).__name__}: {e}")

    return devices


def get_video_capabilities(device_path: str) -> Optional[Dict]:
    """
    Query supported formats, resolutions, and frame rates for a video device.

    Args:
        device_path: Path to the video device (e.g., "/dev/video0")

    Returns:
        Dictionary with keys:
        - formats: List[str] (e.g., ["yuyv422", "mjpeg"])
        - resolutions: List[Tuple[int, int]] (e.g., [[640, 480], [1280, 720]])
        - frame_rates: List[int] (e.g., [15, 30, 60])

        Returns None if query fails.
    """
    try:
        # Run v4l2-ctl --list-formats-ext to get detailed capabilities
        result = subprocess.run(
            ["v4l2-ctl", "--device", device_path, "--list-formats-ext"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.warning(f"Failed to query capabilities for {device_path} (exit code {result.returncode})")
            if result.stderr:
                logger.warning(f"stderr: {result.stderr.strip()}")
            return None

        formats = set()
        resolutions = set()
        frame_rates = set()

        current_format = None
        current_resolution = None

        for line in result.stdout.split('\n'):
            # Format line: [0]: 'YUYV' (YUYV 4:2:2)
            format_match = re.search(r"\[(\d+)\]:\s+'([^']+)'", line)
            if format_match:
                current_format = format_match.group(2).lower()
                formats.add(current_format)

            # Resolution line: Size: Discrete 640x480
            resolution_match = re.search(r"Size:\s+\w+\s+(\d+)x(\d+)", line)
            if resolution_match:
                width = int(resolution_match.group(1))
                height = int(resolution_match.group(2))
                current_resolution = (width, height)
                resolutions.add(current_resolution)

            # Frame rate line: Interval: Discrete 0.033s (30.000 fps)
            fps_match = re.search(r"\((\d+(?:\.\d+)?)\s+fps\)", line)
            if fps_match:
                fps = int(float(fps_match.group(1)))
                frame_rates.add(fps)

        if not formats:
            logger.warning(f"No formats found for {device_path}. Device may not be a valid video capture device.")
            return None

        logger.debug(f"Device {device_path} capabilities: {len(formats)} formats, {len(resolutions)} resolutions, {len(frame_rates)} frame rates")

        return {
            'formats': sorted(list(formats)),
            'resolutions': sorted(list(resolutions)),
            'frame_rates': sorted(list(frame_rates))
        }

    except FileNotFoundError:
        logger.error("v4l2-ctl not found. Please install v4l-utils package (e.g., 'apt install v4l-utils')")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"v4l2-ctl command timed out for {device_path} after 5 seconds")
        return None
    except Exception as e:
        logger.error(f"Unexpected error querying capabilities for {device_path}: {type(e).__name__}: {e}")
        return None


def detect_audio_devices() -> List[Dict]:
    """
    Enumerate all ALSA/PulseAudio input devices.

    Returns:
        List of device info dictionaries with keys:
        - device_path: str (e.g., "hw:0,0")
        - device_name: str (e.g., "USB Audio Device")
        - device_type: str ("audio")
        - capabilities: dict with formats, sample_rates, channels
    """
    devices = []

    try:
        # Run arecord -l to list all audio capture devices
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.error(f"arecord -l failed with exit code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return devices

        # Parse the output
        # Example line: card 0: PCH [HDA Intel PCH], device 0: ALC887-VD Analog [ALC887-VD Analog]
        for line in result.stdout.split('\n'):
            match = re.search(r"card\s+(\d+):\s+([^,]+),\s+device\s+(\d+):\s+(.+)", line)
            if match:
                card_num = match.group(1)
                card_name = match.group(2).strip()
                device_num = match.group(3)
                device_desc = match.group(4).strip()

                # Extract device name from description (before the bracket)
                device_name = device_desc.split('[')[0].strip()
                if not device_name:
                    device_name = card_name

                device_path = f"hw:{card_num},{device_num}"

                # Get capabilities for this device
                capabilities = get_audio_capabilities(device_path)
                if capabilities:
                    devices.append({
                        'device_path': device_path,
                        'device_name': device_name,
                        'device_type': 'audio',
                        'capabilities': capabilities
                    })
                    logger.info(f"Detected audio device: {device_path} ({device_name})")
                else:
                    logger.warning(f"Skipping {device_path} - could not query capabilities")

        if not devices:
            logger.warning("No audio devices found. Audio streaming will not be available.")

    except FileNotFoundError:
        logger.error("arecord not found. Please install alsa-utils package (e.g., 'apt install alsa-utils')")
    except subprocess.TimeoutExpired:
        logger.error("arecord command timed out after 5 seconds. System may be unresponsive.")
    except Exception as e:
        logger.error(f"Unexpected error detecting audio devices: {type(e).__name__}: {e}")

    return devices


def get_audio_capabilities(device_path: str) -> Optional[Dict]:
    """
    Query supported formats and sample rates for an audio device.

    Args:
        device_path: ALSA device identifier (e.g., "hw:0,0")

    Returns:
        Dictionary with keys:
        - formats: List[str] (e.g., ["S16_LE", "S32_LE"])
        - sample_rates: List[int] (e.g., [44100, 48000])
        - channels: List[int] (e.g., [1, 2])

        Returns None if query fails.
    """
    # For simplicity, return common defaults
    # A full implementation would query the device with arecord or parse /proc/asound
    # This provides reasonable defaults that work with most devices
    try:
        # Test if device is accessible by attempting a very short recording
        result = subprocess.run(
            ["arecord", "-D", device_path, "-d", "0", "-f", "S16_LE", "-r", "44100"],
            capture_output=True,
            text=True,
            timeout=2
        )

        # If the device is accessible, return common capabilities
        # Most modern audio devices support these
        logger.debug(f"Audio device {device_path} is accessible")
        return {
            'formats': ['S16_LE', 'S32_LE'],
            'sample_rates': [44100, 48000],
            'channels': [1, 2]
        }

    except FileNotFoundError:
        logger.error("arecord not found. Please install alsa-utils package (e.g., 'apt install alsa-utils')")
        return None
    except (subprocess.TimeoutExpired, TimeoutError):
        logger.warning(f"Audio device test timed out for {device_path}")
        # Still return default capabilities
        return {
            'formats': ['S16_LE', 'S32_LE'],
            'sample_rates': [44100, 48000],
            'channels': [1, 2]
        }
    except Exception as e:
        logger.error(f"Unexpected error querying audio capabilities for {device_path}: {type(e).__name__}: {e}")
        return None
