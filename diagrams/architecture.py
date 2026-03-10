from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Client, Users
from diagrams.onprem.compute import Server
from diagrams.programming.framework import Flask
from diagrams.programming.language import Python
from diagrams.onprem.network import Nginx

with Diagram("RPi Webcam Streamer Architecture", filename="diagrams/architecture", show=False, direction="LR"):

    # Client side
    with Cluster("Web Browser"):
        browser = Client("Browser")
        web_audio = Python("Web Audio API")

    # Server side
    with Cluster("Raspberry Pi"):
        with Cluster("Flask Application"):
            flask_app = Flask("Flask + SocketIO")
            api = Python("REST API")
            video_gen = Python("Video Generator")
            audio_callback = Python("Audio Callback")

        with Cluster("Capture Layer"):
            opencv = Python("OpenCV\n(Video Capture)")
            pyaudio = Python("PyAudio\n(Audio Capture)")

        with Cluster("Hardware"):
            webcam = Server("USB Webcam")
            microphone = Server("USB Microphone")

    # Connections
    browser >> Edge(label="HTTP GET /") >> flask_app
    browser >> Edge(label="POST /api/stream/start") >> api

    api >> Edge(label="cv2.VideoCapture()") >> opencv
    api >> Edge(label="pyaudio.open()") >> pyaudio

    opencv >> Edge(label="read frames") >> webcam
    pyaudio >> Edge(label="callback") >> microphone

    opencv >> Edge(label="JPEG frames") >> video_gen
    video_gen >> Edge(label="HTTP MJPEG\nmultipart/x-mixed-replace") >> browser

    pyaudio >> Edge(label="PCM chunks") >> audio_callback
    audio_callback >> Edge(label="WebSocket\n(Socket.IO)") >> flask_app
    flask_app >> Edge(label="audio_chunk events") >> web_audio
    web_audio >> Edge(label="playback") >> browser
