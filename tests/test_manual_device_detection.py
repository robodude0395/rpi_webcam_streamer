#!/usr/bin/env python3
"""
Manual test script to demonstrate device detection functionality.
This script can be run on a system with actual video/audio devices.
"""

import json
import logging
import device_detector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    print("=" * 60)
    print("Device Detection Test")
    print("=" * 60)

    # Test video device detection
    print("\n1. Detecting video devices...")
    video_devices = device_detector.detect_video_devices()

    if video_devices:
        print(f"   Found {len(video_devices)} video device(s):")
        for device in video_devices:
            print(f"\n   Device: {device['device_name']}")
            print(f"   Path: {device['device_path']}")
            print(f"   Type: {device['device_type']}")
            print(f"   Capabilities:")
            caps = device['capabilities']
            print(f"     - Formats: {', '.join(caps['formats'])}")
            print(f"     - Resolutions: {caps['resolutions'][:3]}...")  # Show first 3
            print(f"     - Frame rates: {caps['frame_rates']}")
    else:
        print("   No video devices found (or v4l2-ctl not available)")

    # Test audio device detection
    print("\n2. Detecting audio devices...")
    audio_devices = device_detector.detect_audio_devices()

    if audio_devices:
        print(f"   Found {len(audio_devices)} audio device(s):")
        for device in audio_devices:
            print(f"\n   Device: {device['device_name']}")
            print(f"   Path: {device['device_path']}")
            print(f"   Type: {device['device_type']}")
            print(f"   Capabilities:")
            caps = device['capabilities']
            print(f"     - Formats: {', '.join(caps['formats'])}")
            print(f"     - Sample rates: {caps['sample_rates']}")
            print(f"     - Channels: {caps['channels']}")
    else:
        print("   No audio devices found (or arecord not available)")

    # Test JSON serialization
    print("\n3. Testing JSON serialization...")
    all_devices = {
        'video': video_devices,
        'audio': audio_devices
    }

    try:
        json_output = json.dumps(all_devices, indent=2)
        print("   ✓ JSON serialization successful")
        print(f"   JSON size: {len(json_output)} bytes")
    except Exception as e:
        print(f"   ✗ JSON serialization failed: {e}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
