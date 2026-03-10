"""
Low Latency Audio Streamer
Optimized for minimal delay
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
    print("✗ PyAudio not available")

# Audio configuration - optimized for low latency
FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
CHANNELS = 1  # Mono reduces data size
RATE = 22050  # Lower sample rate = lower latency (was 44100)
CHUNK = 256   # Smaller chunks = lower latency (was 1024)

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
    """Stream audio from microphone with minimal latency"""
    if not PYAUDIO_AVAILABLE:
        yield b"PyAudio not available"
        return

    audio = pyaudio.PyAudio()

    try:
        # Try device 1 first, then 0
        device_index = 1
        try:
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK,
                stream_callback=None  # Blocking mode for simpler code
            )
            print(f"✓ Opened audio device {device_index}")
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
            print(f"✓ Opened audio device {device_index}")

        # Send WAV header
        bits_per_sample = 16
        wav_header = gen_wav_header(RATE, bits_per_sample, CHANNELS)
        yield wav_header

        print(f"✓ Streaming audio at {RATE}Hz, {CHANNELS} channel(s), chunk size {CHUNK}")
        print(f"  Theoretical latency: ~{(CHUNK/RATE)*1000:.1f}ms per chunk")

        # Stream audio chunks
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            yield data

    except Exception as e:
        print(f"✗ Error: {e}")
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
    """Low latency test page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Low Latency Audio Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; margin-top: 0; }
            button {
                padding: 12px 24px;
                font-size: 16px;
                cursor: pointer;
                margin: 10px 5px;
                border: none;
                border-radius: 5px;
                transition: all 0.3s;
            }
            .start-btn {
                background: #4CAF50;
                color: white;
            }
            .start-btn:hover { background: #45a049; }
            .stop-btn {
                background: #f44336;
                color: white;
            }
            .stop-btn:hover { background: #da190b; }
            #status {
                margin-top: 20px;
                padding: 15px;
                background: #e3f2fd;
                border-left: 4px solid #2196F3;
                border-radius: 4px;
            }
            .info {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }
            .info h3 { margin-top: 0; color: #856404; }
            .info ul { margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 Low Latency Audio Test</h1>

            <div class="info">
                <h3>Optimizations Applied:</h3>
                <ul>
                    <li>Sample rate: 22050 Hz (lower = less latency)</li>
                    <li>Mono audio (1 channel)</li>
                    <li>Small chunk size: 256 samples (~11ms latency)</li>
                    <li>No browser buffering</li>
                </ul>
            </div>

            <button class="start-btn" onclick="startAudio()">▶ Start Audio</button>
            <button class="stop-btn" onclick="stopAudio()">⏹ Stop Audio</button>

            <div id="status">Status: Ready to stream</div>

            <audio id="audio" controls style="display:none; width: 100%; margin-top: 20px;"></audio>
        </div>

        <script>
            let audio = document.getElementById('audio');
            let status = document.getElementById('status');

            function startAudio() {
                // Clear any existing source
                audio.src = '';

                // Set source with cache-busting
                audio.src = '/audio?t=' + Date.now();
                audio.style.display = 'block';

                // Minimize buffering
                audio.preload = 'none';

                // Try to play
                audio.play().then(() => {
                    status.textContent = '✓ Status: Streaming audio (low latency mode)';
                    status.style.background = '#d4edda';
                    status.style.borderColor = '#28a745';
                }).catch(err => {
                    status.textContent = '✗ Status: Error - ' + err.message;
                    status.style.background = '#f8d7da';
                    status.style.borderColor = '#dc3545';
                    console.error('Playback error:', err);
                });
            }

            function stopAudio() {
                audio.pause();
                audio.src = '';
                audio.style.display = 'none';
                status.textContent = 'Status: Stopped';
                status.style.background = '#e3f2fd';
                status.style.borderColor = '#2196F3';
            }

            // Monitor audio element
            audio.addEventListener('waiting', () => {
                console.log('Buffering...');
            });

            audio.addEventListener('playing', () => {
                console.log('Playing');
            });

            audio.addEventListener('error', (e) => {
                console.error('Audio error:', e);
                status.textContent = '✗ Status: Stream error';
                status.style.background = '#f8d7da';
            });
        </script>
    </body>
    </html>
    """

@app.route('/audio')
def audio():
    """Low latency audio endpoint"""
    return Response(
        stream_audio(),
        mimetype='audio/x-wav',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Low Latency Audio Streamer")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Sample Rate: {RATE} Hz")
    print(f"  Channels: {CHANNELS}")
    print(f"  Chunk Size: {CHUNK} samples")
    print(f"  Theoretical Latency: ~{(CHUNK/RATE)*1000:.1f}ms per chunk")

    if not PYAUDIO_AVAILABLE:
        print("\n⚠ WARNING: PyAudio not available!")
        print("Install with: sudo apt-get install python3-pyaudio\n")

    print("\nStarting server on http://0.0.0.0:5000")
    print("Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
