"""
Real-time Audio Streamer using WebSocket
True low-latency streaming with Web Audio API
"""
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Try to import pyaudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    print("✓ PyAudio available")
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("✗ PyAudio not available")

# Audio configuration - optimized for real-time
FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
CHANNELS = 1
RATE = 16000  # Lower rate for lower latency
CHUNK = 512   # Balance between latency and stability

# Global audio stream
audio_stream = None
audio_input = None
streaming = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Real-time Audio Stream</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
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
        .metrics {
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Real-time Audio Stream</h1>

        <div class="info">
            <strong>WebSocket + Web Audio API</strong><br>
            True real-time streaming with minimal buffering
        </div>

        <button class="start-btn" onclick="startStream()">▶ Start Stream</button>
        <button class="stop-btn" onclick="stopStream()">⏹ Stop Stream</button>

        <div id="status">Status: Ready</div>
        <div id="metrics" class="metrics" style="display:none;">
            Packets received: <span id="packets">0</span><br>
            Buffer size: <span id="buffer">0</span> samples<br>
            Latency estimate: <span id="latency">0</span>ms
        </div>
    </div>

    <script>
        const socket = io();
        let audioContext = null;
        let nextPlayTime = 0;
        let packetsReceived = 0;
        let isStreaming = false;

        const SAMPLE_RATE = 16000;
        const CHANNELS = 1;

        function startStream() {
            if (isStreaming) return;

            // Create audio context
            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: SAMPLE_RATE,
                latencyHint: 'interactive'  // Minimize latency
            });

            nextPlayTime = audioContext.currentTime;
            packetsReceived = 0;
            isStreaming = true;

            // Request audio stream
            socket.emit('start_audio');

            updateStatus('Connecting...', '#fff3cd');
            document.getElementById('metrics').style.display = 'block';
        }

        function stopStream() {
            if (!isStreaming) return;

            isStreaming = false;
            socket.emit('stop_audio');

            if (audioContext) {
                audioContext.close();
                audioContext = null;
            }

            updateStatus('Stopped', '#e3f2fd');
            document.getElementById('metrics').style.display = 'none';
        }

        function updateStatus(text, color) {
            const status = document.getElementById('status');
            status.textContent = 'Status: ' + text;
            status.style.background = color;
        }

        // Receive audio data
        socket.on('audio_chunk', function(data) {
            if (!isStreaming || !audioContext) return;

            packetsReceived++;

            try {
                // Convert hex string to Int16Array
                const bytes = new Uint8Array(data.length / 2);
                for (let i = 0; i < bytes.length; i++) {
                    bytes[i] = parseInt(data.substr(i * 2, 2), 16);
                }

                // Create Int16Array from bytes
                const int16Array = new Int16Array(bytes.buffer);

                // Convert to Float32Array for Web Audio API
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {
                    float32Array[i] = int16Array[i] / 32768.0;  // Normalize to -1.0 to 1.0
                }

                // Create audio buffer
                const audioBuffer = audioContext.createBuffer(CHANNELS, float32Array.length, SAMPLE_RATE);
                audioBuffer.getChannelData(0).set(float32Array);

                // Create buffer source
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);

                // Schedule playback
                if (nextPlayTime < audioContext.currentTime) {
                    nextPlayTime = audioContext.currentTime;
                }

                source.start(nextPlayTime);
                nextPlayTime += audioBuffer.duration;

                // Update metrics
                document.getElementById('packets').textContent = packetsReceived;
                document.getElementById('buffer').textContent = Math.round((nextPlayTime - audioContext.currentTime) * SAMPLE_RATE);
                document.getElementById('latency').textContent = Math.round((nextPlayTime - audioContext.currentTime) * 1000);

                if (packetsReceived === 1) {
                    updateStatus('Streaming (real-time)', '#d4edda');
                }

            } catch (e) {
                console.error('Error processing audio:', e);
            }
        });

        socket.on('connect', function() {
            console.log('Connected to server');
        });

        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            if (isStreaming) {
                stopStream();
                updateStatus('Disconnected', '#f8d7da');
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    stop_audio_stream()

@socketio.on('start_audio')
def handle_start_audio():
    global audio_stream, audio_input, streaming

    if not PYAUDIO_AVAILABLE:
        emit('error', {'message': 'PyAudio not available'})
        return

    if streaming:
        return

    try:
        audio_stream = pyaudio.PyAudio()

        # Try device 1, fallback to 0
        device_index = 1
        try:
            audio_input = audio_stream.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK,
                stream_callback=audio_callback
            )
            print(f'Started audio stream on device {device_index}')
        except:
            device_index = 0
            audio_input = audio_stream.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK,
                stream_callback=audio_callback
            )
            print(f'Started audio stream on device {device_index}')

        streaming = True
        audio_input.start_stream()

    except Exception as e:
        print(f'Error starting audio: {e}')
        emit('error', {'message': str(e)})
        stop_audio_stream()

@socketio.on('stop_audio')
def handle_stop_audio():
    stop_audio_stream()

def stop_audio_stream():
    global audio_stream, audio_input, streaming

    streaming = False

    if audio_input:
        try:
            audio_input.stop_stream()
            audio_input.close()
        except:
            pass
        audio_input = None

    if audio_stream:
        try:
            audio_stream.terminate()
        except:
            pass
        audio_stream = None

    print('Stopped audio stream')

def audio_callback(in_data, frame_count, time_info, status):
    """PyAudio callback - sends data via WebSocket"""
    if streaming and in_data:
        # Convert to hex string for JSON transmission
        hex_data = in_data.hex()
        socketio.emit('audio_chunk', hex_data)

    return (None, pyaudio.paContinue)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Real-time Audio Streamer (WebSocket)")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Sample Rate: {RATE} Hz")
    print(f"  Channels: {CHANNELS}")
    print(f"  Chunk Size: {CHUNK} samples")
    print(f"  Expected Latency: ~{(CHUNK/RATE)*1000:.0f}ms + network")

    if not PYAUDIO_AVAILABLE:
        print("\n⚠ WARNING: PyAudio not available!")
        print("Install with: sudo apt-get install python3-pyaudio\n")

    print("\nStarting server on http://0.0.0.0:5000")
    print("Press Ctrl+C to stop\n")

    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_audio_stream()
