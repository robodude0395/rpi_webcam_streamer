"""
Simple Audio Streamer Test
Minimal app to test audio streaming via HTTP
"""
from flask import Flask, Response
import time

app = Flask(__name__)

# Try to import pyaudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    print("✓ PyAudio available")
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("✗ PyAudio not available - install with: sudo apt-get install python3-pyaudio")

# Audio configuration
FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
CHANNELS = 2
RATE = 44100
CHUNK = 1024

def gen_wav_header(sample_rate, bits_per_sample, channels):
    """Generate WAV header for audio streaming"""
    datasize = 2000 * 10**6
    o = bytes("RIFF", 'ascii')
    o += (datasize + 36).to_bytes(4, 'little')
    o += bytes("WAVE", 'ascii')
    o += bytes("fmt ", 'ascii')
    o += (16).to_bytes(4, 'little')
    o += (1).to_bytes(2, 'little')
    o += (channels).to_bytes(2, 'little')
    o += (sample_rate).to_bytes(4, 'little')
    o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')
    o += (channels * bits_per_sample // 8).to_bytes(2, 'little')
    o += (bits_per_sample).to_bytes(2, 'little')
    o += bytes("data", 'ascii')
    o += (datasize).to_bytes(4, 'little')
    return o

def stream_audio():
    """Stream audio from microphone"""
    if not PYAUDIO_AVAILABLE:
        yield b"PyAudio not available"
        return

    audio = pyaudio.PyAudio()

    # List available devices
    print("\nAvailable audio input devices:")
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']} - {info['maxInputChannels']} channels")

    try:
        # Open audio stream - try device index 1 first, then 0
        device_index = 1
        try:
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )
            print(f"\n✓ Opened audio device {device_index}")
        except:
            device_index = 0
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )
            print(f"\n✓ Opened audio device {device_index}")

        # Send WAV header first
        bits_per_sample = 16
        wav_header = gen_wav_header(RATE, bits_per_sample, CHANNELS)
        yield wav_header

        print("✓ Streaming audio... (Ctrl+C to stop)")

        # Stream audio chunks
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            yield data

    except Exception as e:
        print(f"✗ Error streaming audio: {e}")
        yield b""
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
        audio.terminate()

@app.route('/')
def index():
    """Simple test page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Audio Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                margin: 10px 5px;
            }
            #status {
                margin-top: 20px;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Simple Audio Stream Test</h1>
        <p>Click the button below to start audio streaming:</p>

        <button onclick="startAudio()">Start Audio</button>
        <button onclick="stopAudio()">Stop Audio</button>

        <div id="status">Status: Ready</div>

        <audio id="audio" controls style="display:none;"></audio>

        <script>
            let audio = document.getElementById('audio');
            let status = document.getElementById('status');

            function startAudio() {
                audio.src = '/audio';
                audio.style.display = 'block';
                audio.play().then(() => {
                    status.textContent = 'Status: Playing audio stream';
                    status.style.background = '#90EE90';
                }).catch(err => {
                    status.textContent = 'Status: Error - ' + err.message;
                    status.style.background = '#FFB6C1';
                });
            }

            function stopAudio() {
                audio.pause();
                audio.src = '';
                audio.style.display = 'none';
                status.textContent = 'Status: Stopped';
                status.style.background = '#f0f0f0';
            }
        </script>
    </body>
    </html>
    """

@app.route('/audio')
def audio():
    """Stream audio endpoint"""
    return Response(stream_audio(), mimetype='audio/x-wav')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Simple Audio Stream Test Server")
    print("="*50)

    if not PYAUDIO_AVAILABLE:
        print("\n⚠ WARNING: PyAudio not available!")
        print("Install with: sudo apt-get install python3-pyaudio")
        print("\nServer will start but audio streaming won't work.\n")

    print("\nStarting server on http://0.0.0.0:5000")
    print("Open in browser: http://localhost:5000")
    print("\nPress Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
