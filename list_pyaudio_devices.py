#!/usr/bin/env python3
"""
Helper script to list PyAudio devices and find the correct index for your audio device.
Run this to see what device index to use in the web UI.
"""

try:
    import pyaudio

    p = pyaudio.PyAudio()

    print("=" * 60)
    print("PyAudio Device List")
    print("=" * 60)

    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            print(f"\nDevice {i}: {info['name']}")
            print(f"  Max Input Channels: {info['maxInputChannels']}")
            print(f"  Max Output Channels: {info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {info['defaultSampleRate']}")

            if info['maxInputChannels'] > 0:
                print(f"  ✓ This is an INPUT device (microphone/capture)")
        except Exception as e:
            print(f"\nDevice {i}: Error querying - {e}")

    p.terminate()

    print("\n" + "=" * 60)
    print("Use the device number for 'USB Audio' or your webcam")
    print("=" * 60)

except ImportError:
    print("PyAudio not installed. Install with: sudo apt-get install python3-pyaudio")
except Exception as e:
    print(f"Error: {e}")
