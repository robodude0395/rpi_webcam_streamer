# Audio Troubleshooting Guide

## Segmentation Fault When Enabling Audio

If you get a segmentation fault when enabling audio, this is typically caused by ALSA trying to access misconfigured audio plugins (Jack, PulseAudio virtual devices, etc.).

### Quick Fix: Create ALSA Configuration

Create a file `~/.asoundrc` with the following content:

```bash
# Disable problematic ALSA plugins
pcm.!default {
    type hw
    card 2  # Change to your USB audio card number
    device 0
}

ctl.!default {
    type hw
    card 2  # Change to match your card number
}
```

To find your card number, run:
```bash
arecord -l
```

Look for your USB audio device and note the card number (e.g., "card 2").

### Alternative: Suppress ALSA Errors

Set environment variables before running the application:

```bash
export ALSA_CARD=2  # Your USB audio card number
export AUDIODEV=hw:2,0  # Your ALSA device path
python main.py
```

### Verify PyAudio Device Mapping

Run the helper script to see PyAudio device indices:

```bash
python list_pyaudio_devices.py
```

This will show all available audio devices and their PyAudio indices. Use this information to verify the correct device is being selected.

## Common ALSA Errors

### "Unknown PCM" Errors

These warnings are harmless and occur when ALSA tries to probe virtual devices that don't exist:
- `Unknown PCM front`
- `Unknown PCM surround51`
- `Unknown PCM spdif`

The application handles these gracefully, but you can suppress them with the `~/.asoundrc` configuration above.

### "jack server is not running"

This error occurs when PyAudio tries to use the Jack audio plugin. The application doesn't need Jack, so this can be safely ignored or suppressed with the ALSA configuration.

## Testing Audio Devices

### Test with arecord

```bash
# List devices
arecord -l

# Test recording from your USB device
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav

# Play back the recording
aplay test.wav
```

### Test with PyAudio

```bash
python list_pyaudio_devices.py
```

## Application Behavior

The application is designed to gracefully handle audio failures:

1. If audio initialization fails, the stream continues with video only
2. Audio errors are logged as warnings, not errors
3. The web UI will show video even if audio fails

## Debug Logging

To see detailed audio initialization logs, check the console output when starting the stream. Look for:

```
INFO - Looking for audio device: hw:2,0
INFO - Mapped hw:2,0 to PyAudio device X: [device name]
INFO - Opening audio device index X
INFO - Audio ready: device hw:2,0, 16000Hz, 1ch
```

If you see warnings instead, audio initialization failed and the stream will be video-only.
