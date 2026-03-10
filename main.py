import subprocess
from flask import Flask, Response

app = Flask(__name__)

# FFmpeg command to capture YUYV webcam and output MJPEG frames
FFMPEG_CMD = [
    "ffmpeg",
    "-f", "v4l2",
    "-input_format", "yuyv422",      # YUYV webcam
    "-framerate", "30",               # FPS
    "-video_size", "640x480",         # Resolution
    "-i", "/dev/video0",              # Your webcam device
    "-f", "mjpeg",
    "pipe:1"                          # Output to stdout
]

def gen():
    """Generate MJPEG frames from FFmpeg stdout"""
    process = subprocess.Popen(FFMPEG_CMD, stdout=subprocess.PIPE, bufsize=10**8)
    while True:
        # MJPEG frames are separated by 0xFFD8 (start) and 0xFFD9 (end)
        data = b''
        while True:
            byte = process.stdout.read(1)
            if not byte:
                break
            data += byte
            if data[-2:] == b'\xff\xd9':  # JPEG end marker
                break
        if data:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<h1>YUYV Webcam Stream</h1><img src='/video_feed'>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
