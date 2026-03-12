# Audio Segmentation Fault Fix - Summary

## Problem
When enabling audio in the web UI, the application crashed with a segmentation fault. The error logs showed:
- Multiple ALSA "Unknown PCM" errors (front, surround51, spdif, etc.)
- Jack audio server connection failures
- Final segmentation fault

## Root Cause
PyAudio was enumerating all ALSA devices during initialization, including misconfigured virtual devices and plugins (Jack, PulseAudio surround sound devices, etc.) that don't exist on the Raspberry Pi. This caused ALSA to crash.

## Solution Implemented

### 1. Device Mapping Function (`get_pyaudio_device_index_for_alsa`)
- Safely maps ALSA device paths (like "hw:2,0") to PyAudio device indices
- Catches exceptions during device enumeration to prevent crashes
- Logs the mapping for debugging

### 2. Enhanced `/api/devices` Endpoint
- Now includes `pyaudio_index` for each audio device
- Frontend receives both ALSA path and PyAudio index

### 3. Updated Stream Configuration
- `StreamConfig` now includes `audio_device_name` field
- `start_stream` endpoint accepts both `audio_device_name` and `audio_device_index`
- Automatically maps ALSA device name to PyAudio index when starting stream

### 4. Frontend Updates
- Stores PyAudio index as data attribute on audio device options
- Sends both `audio_device_name` (ALSA path) and `audio_device_index` (PyAudio index)
- Server uses the correct PyAudio index to open the device

### 5. Improved Error Handling
- Audio initialization wrapped in try-except
- Partial audio initialization is cleaned up on failure
- Stream continues with video-only if audio fails

## Files Changed

1. `main.py`
   - Added `audio_device_name` to `StreamConfig`
   - Added `get_pyaudio_device_index_for_alsa()` function
   - Updated `get_devices()` to include PyAudio indices
   - Updated `start_stream()` to map ALSA devices to PyAudio indices
   - Improved error handling in audio initialization

2. `static/index.html`
   - Store PyAudio index in option data attributes
   - Send both `audio_device_name` and `audio_device_index` to server

3. New Files
   - `list_pyaudio_devices.py` - Helper script to list PyAudio devices
   - `asound.conf.example` - Example ALSA configuration to prevent errors
   - `docs/AUDIO_TROUBLESHOOTING.md` - Comprehensive troubleshooting guide

## Testing

To test the fix:

1. **Check PyAudio device mapping:**
   ```bash
   python list_pyaudio_devices.py
   ```

2. **Optional: Create ALSA config to suppress errors:**
   ```bash
   cp asound.conf.example ~/.asoundrc
   # Edit ~/.asoundrc and set your card number
   ```

3. **Start the application:**
   ```bash
   python main.py
   ```

4. **In the web UI:**
   - Select your video device
   - Enable audio checkbox
   - Select "USB Audio (hw:2,0)" from audio device dropdown
   - Click "Start Stream"

5. **Check logs for:**
   ```
   INFO - Mapped hw:2,0 to PyAudio device X
   INFO - Opening audio device index X
   INFO - Audio ready: device hw:2,0, 16000Hz, 1ch
   ```

## Fallback Behavior

If audio still fails:
- The application logs a warning
- Stream continues with video only
- No crash or segmentation fault
- User can still view video feed

## Next Steps

If you still experience issues:

1. Run `python list_pyaudio_devices.py` to verify device detection
2. Check `docs/AUDIO_TROUBLESHOOTING.md` for detailed solutions
3. Create `~/.asoundrc` to suppress ALSA plugin errors
4. Verify your USB audio device works with `arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav`
