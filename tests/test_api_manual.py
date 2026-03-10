#!/usr/bin/env python3
"""
Manual test script for REST API endpoints.
This script demonstrates how to use the webcam streamer API.

Usage:
    python test_api_manual.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"


def test_get_devices():
    """Test GET /api/devices endpoint"""
    print("\n=== Testing GET /api/devices ===")
    response = requests.get(f"{BASE_URL}/api/devices")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_start_stream(video_device, audio_enabled=False, audio_device=None):
    """Test POST /api/stream/start endpoint"""
    print("\n=== Testing POST /api/stream/start ===")
    config = {
        "video_device": video_device,
        "video_format": "yuyv422",
        "resolution": [640, 480],
        "frame_rate": 30,
        "audio_enabled": audio_enabled,
        "audio_device": audio_device
    }
    print(f"Config: {json.dumps(config, indent=2)}")
    response = requests.post(f"{BASE_URL}/api/stream/start", json=config)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_get_status():
    """Test GET /api/stream/status endpoint"""
    print("\n=== Testing GET /api/stream/status ===")
    response = requests.get(f"{BASE_URL}/api/stream/status")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_stop_stream():
    """Test POST /api/stream/stop endpoint"""
    print("\n=== Testing POST /api/stream/stop ===")
    response = requests.post(f"{BASE_URL}/api/stream/stop")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def main():
    """Run all API tests"""
    print("=" * 60)
    print("Webcam Streamer REST API Manual Test")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print("Make sure the Flask server is running on port 8080")
    print("=" * 60)

    try:
        # Test device detection
        devices = test_get_devices()

        # Check if we have any video devices
        if devices.get('success') and devices.get('video_devices'):
            video_device = devices['video_devices'][0]['device_path']
            print(f"\nFound video device: {video_device}")

            # Test starting stream
            test_start_stream(video_device)

            # Wait a bit
            print("\nWaiting 2 seconds...")
            time.sleep(2)

            # Test status
            test_get_status()

            # Test stopping stream
            test_stop_stream()

            # Test status again
            test_get_status()
        else:
            print("\nNo video devices found. Skipping stream tests.")

    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to the server.")
        print("Make sure the Flask server is running:")
        print("  python main.py")
    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    main()
