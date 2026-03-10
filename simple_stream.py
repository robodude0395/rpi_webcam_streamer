#!/usr/bin/env python3
"""
Simple webcam streamer - just video and audio, no complexity.
"""
import subprocess
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# Configuration - adjust these for your setup
VIDEO_DEVICE = "/dev/video1"  # Your USB camera
AUDIO_DEVICE = "hw:2,0"       # Your USB audio
WIDTH = 640
HEIGHT = 480
FPS = 30

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Simple Webcam Stream</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #222;
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
        }
        h1 { margin-bottom: 20px; }
        img {
            max-width: 100%;
            border: 2px solid #444;
            border-radius: 8px;
        }
        .audio-link {
            display: inline-block;
            margin-top: 20px;
            padding: 15px 30px;
            background: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 18px;
        }
        .audio-link:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <h1>Webcam Stream</h1>
    <img src="/video" alt="Video Stream">
    <br>
    <a href="/audio" class="audio-link" target="_blank">🔊 Open Audio Stream</a>
    <p style="color: #999; margin-top: 10px;">Click to open audio in a new tab</p>
</body>
</html>
"""

def generate_video():
    """Stream MJPEG video from webcam"""
    cmd = [
        'ffmpeg',
        '-f', 'v4l2',
        '-input_format', 'mjpeg',
        '-video_size', f'{WIDTH}x{HEIGHT}',
        '-framerate', str(FPS),
        '-i', VIDEO_DEVICE,
        '-f', 'mjpeg',
        '-q:v', '5',
        'pipe:1'
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)

    try:
        while True:
            # Read MJPEG frame
            data = b''
            while True:
                byte = process.stdout.read(1)
                if not byte:
                    return
                data += byte
                # JPEG end marker
                if data[-2:] == b'\xff\xd9':
                    break

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
    finally:
        process.terminate()

def generate_audio():
    """Stream MP3 audio from microphone"""
    cmd = [
        'ffmpeg',
        '-f', 'alsa',
        '-i', AUDIO_DEVICE,
        '-ar', '44100',
        '-ac', '1',
        '-b:a', '128k',
        '-f', 'mp3',
        'pipe:1'
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)

    try:
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            yield chunk
    finally:
        process.terminate()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video')
def video():
    return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/audio')
def audio():
    return Response(generate_audio(), mimetype='audio/mpeg')

if __name__ == '__main__':
    print(f"Starting simple webcam streamer...")
    print(f"Video: {VIDEO_DEVICE} at {WIDTH}x{HEIGHT}@{FPS}fps")
    print(f"Audio: {AUDIO_DEVICE}")
    print(f"\nOpen http://0.0.0.0:8080 in your browser")
    print(f"Click the audio button to open audio in a new tab")
    app.run(host='0.0.0.0', port=8080, threaded=True)
