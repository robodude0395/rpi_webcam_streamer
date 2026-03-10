"""
Raspberry Pi Webcam Streamer - Optimized Real-time Version
Efficient video + audio streaming for resource-constrained devices
"""
import time
import logging
import threading
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from typing import Optional
from dataclasses import dataclass
from enum import Enum
import device_detector
import cv2

# Try to import pyaudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not PYAUDIO_AVAILABLE:
    logger.warning("PyAudio not available. Install with: sudo apt-get install python3-pyaudio")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


class StreamState(Enum):
    """Stream state enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class StreamConfig:
    """Configuration for video and audio streams - optimized for RPi"""
    video_device_index: int = 0
    resolution: tuple = (640, 480)
    frame_rate: int = 15  # Lower default for RPi efficiency
    audio_enabled: bool = False
    audio_device_index: int = 1
    audio_sample_rate: int = 16000  # Lower rate for efficiency
    audio_channels: int = 1  # Mono for efficiency
    audio_chunk_size: int = 512  # Balance latency/CPU


# Global state
current_config = StreamConfig()
video_capture: Optional[cv2.VideoCapture] = None
audio_stream = None
audio_input_stream = None
stream_state = StreamState.STOPPED
stream_start_time: Optional[float] = None
stream_error_message: Optional[str] = None
audio_streaming = False


def gen_video():
    """Generate MJPEG frames - optimized for efficiency"""
    global video_capture

    if not video_capture or not video_capture.isOpened():
        logger.error("No video capture running")
        return

    try:
        while video_capture and video_capture.isOpened():
            ret, frame = video_capture.read()
            if not ret:
                logger.warning("Failed to read frame")
                break

            # Resize if needed
            if frame.shape[1] != current_config.resolution[0] or frame.shape[0] != current_config.resolution[1]:
                frame = cv2.resize(frame, current_config.resolution)

            # Encode as JPEG with quality setting for efficiency
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # 80% quality
            ret, jpeg = cv2.imencode('.jpg', frame, encode_param)
            if not ret:
                continue

            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Frame rate control
            time.sleep(1.0 / current_config.frame_rate)

    except Exception as e:
        logger.error(f"Error in video generator: {e}")
    finally:
        logger.info("Video generator stopped")


def audio_callback(in_data, frame_count, time_info, status):
    """PyAudio callback - efficient real-time streaming"""
    if audio_streaming and in_data:
        # Send directly via WebSocket
        socketio.emit('audio_chunk', in_data.hex(), namespace='/audio')
    return (None, pyaudio.paContinue)


# WebSocket Event Handlers

@socketio.on('connect', namespace='/audio')
def handle_audio_connect():
    """Handle client connection"""
    logger.info("Audio client connected")


@socketio.on('disconnect', namespace='/audio')
def handle_audio_disconnect():
    """Handle client disconnection"""
    logger.info("Audio client disconnected")


@socketio.on('start_audio', namespace='/audio')
def handle_start_audio():
    """Start audio streaming for connected client"""
    global audio_stream, audio_input_stream, audio_streaming

    if not PYAUDIO_AVAILABLE:
        emit('error', {'message': 'PyAudio not available'})
        return

    if not current_config.audio_enabled:
        emit('error', {'message': 'Audio not enabled in stream config'})
        return

    if audio_streaming:
        logger.info("Audio already streaming")
        return

    try:
        if not audio_stream:
            audio_stream = pyaudio.PyAudio()

        if not audio_input_stream:
            audio_input_stream = audio_stream.open(
                format=pyaudio.paInt16,
                channels=current_config.audio_channels,
                rate=current_config.audio_sample_rate,
                input=True,
                input_device_index=current_config.audio_device_index,
                frames_per_buffer=current_config.audio_chunk_size,
                stream_callback=audio_callback
            )

        audio_streaming = True
        audio_input_stream.start_stream()
        logger.info(f"Started real-time audio streaming: {current_config.audio_sample_rate}Hz, {current_config.audio_channels}ch")

    except Exception as e:
        logger.error(f"Error starting audio: {e}")
        emit('error', {'message': str(e)})


@socketio.on('stop_audio', namespace='/audio')
def handle_stop_audio():
    """Stop audio streaming"""
    global audio_streaming
    audio_streaming = False
    logger.info("Stopped audio streaming for client")


# REST API Endpoints

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get available devices"""
    try:
        video_devices = device_detector.detect_video_devices()
        audio_devices = device_detector.detect_audio_devices()

        return jsonify({
            'success': True,
            'video_devices': video_devices,
            'audio_devices': audio_devices,
            'pyaudio_available': PYAUDIO_AVAILABLE
        })
    except Exception as e:
        logger.error(f"Error detecting devices: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'DEVICE_DETECTION_ERROR',
                'message': 'Failed to detect devices',
                'details': str(e)
            }
        }), 500
def _cleanup_streams():
    """Internal helper to cleanup all stream resources"""
    global video_capture, audio_stream, audio_input_stream, audio_streaming
    global stream_state, stream_start_time, stream_error_message

    logger.info("Cleaning up existing streams...")

    # Stop audio
    audio_streaming = False

    if audio_input_stream:
        try:
            audio_input_stream.stop_stream()
            audio_input_stream.close()
        except Exception as e:
            logger.warning(f"Error closing audio input stream: {e}")
        audio_input_stream = None

    if audio_stream:
        try:
            audio_stream.terminate()
        except Exception as e:
            logger.warning(f"Error terminating audio stream: {e}")
        audio_stream = None

    # Stop video
    if video_capture:
        try:
            video_capture.release()
        except Exception as e:
            logger.warning(f"Error releasing video capture: {e}")
        video_capture = None

    # Reset state
    stream_state = StreamState.STOPPED
    stream_start_time = None
    stream_error_message = None

    logger.info("Stream cleanup complete")


@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """Start video and audio streams"""
    global current_config, video_capture, audio_stream, audio_input_stream
    global stream_state, stream_start_time, stream_error_message, audio_streaming

    try:
        # If stream is already running or starting, clean up first
        if stream_state in [StreamState.RUNNING, StreamState.STARTING]:
            logger.warning("Stream already active, cleaning up before restart")
            _cleanup_streams()
            # Small delay to ensure resources are released
            time.sleep(0.1)

        data = request.get_json() or {}

        # Update configuration
        stream_state = StreamState.STARTING
        current_config.video_device_index = data.get('video_device_index', 0)

        resolution = data.get('resolution', [640, 480])
        current_config.resolution = tuple(resolution) if isinstance(resolution, list) else (640, 480)

        current_config.frame_rate = data.get('frame_rate', 15)
        current_config.audio_enabled = data.get('audio_enabled', False)
        current_config.audio_device_index = data.get('audio_device_index', 1)
        current_config.audio_sample_rate = data.get('audio_sample_rate', 16000)
        current_config.audio_channels = data.get('audio_channels', 1)
        current_config.audio_chunk_size = data.get('audio_chunk_size', 512)

        # Start video capture
        try:
            video_capture = cv2.VideoCapture(current_config.video_device_index)

            if not video_capture.isOpened():
                raise Exception(f"Failed to open video device {current_config.video_device_index}")

            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, current_config.resolution[0])
            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, current_config.resolution[1])
            video_capture.set(cv2.CAP_PROP_FPS, current_config.frame_rate)

            logger.info(f"Started video: device {current_config.video_device_index}, {current_config.resolution[0]}x{current_config.resolution[1]}@{current_config.frame_rate}fps")

        except Exception as e:
            stream_state = StreamState.ERROR
            stream_error_message = f"Failed to start video: {str(e)}"
            logger.error(stream_error_message)
            _cleanup_streams()
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VIDEO_START_FAILED',
                    'message': stream_error_message
                }
            }), 500

        # Prepare audio (will start when client connects)
        if current_config.audio_enabled and PYAUDIO_AVAILABLE:
            try:
                if not audio_stream:
                    audio_stream = pyaudio.PyAudio()

                # Pre-open audio stream
                if not audio_input_stream:
                    audio_input_stream = audio_stream.open(
                        format=pyaudio.paInt16,
                        channels=current_config.audio_channels,
                        rate=current_config.audio_sample_rate,
                        input=True,
                        input_device_index=current_config.audio_device_index,
                        frames_per_buffer=current_config.audio_chunk_size,
                        stream_callback=audio_callback
                    )

                logger.info(f"Audio ready: device {current_config.audio_device_index}, {current_config.audio_sample_rate}Hz, {current_config.audio_channels}ch")

            except Exception as e:
                logger.warning(f"Audio setup failed: {e}. Continuing with video only.")
                current_config.audio_enabled = False

        # Update state
        stream_state = StreamState.RUNNING
        stream_start_time = time.time()
        stream_error_message = None

        return jsonify({
            'success': True,
            'message': 'Stream started successfully',
            'config': {
                'video_device_index': current_config.video_device_index,
                'resolution': list(current_config.resolution),
                'frame_rate': current_config.frame_rate,
                'audio_enabled': current_config.audio_enabled,
                'audio_device_index': current_config.audio_device_index,
                'audio_sample_rate': current_config.audio_sample_rate,
                'audio_channels': current_config.audio_channels
            }
        })

    except Exception as e:
        stream_state = StreamState.ERROR
        stream_error_message = str(e)
        logger.error(f"Error starting stream: {e}")
        _cleanup_streams()
        return jsonify({
            'success': False,
            'error': {
                'code': 'STREAM_START_ERROR',
                'message': 'Failed to start stream',
                'details': str(e)
            }
        }), 500


@app.route('/api/stream/stop', methods=['POST'])
def stop_stream():
    """Stop all streams"""
    try:
        _cleanup_streams()

        return jsonify({
            'success': True,
            'message': 'Stream stopped successfully'
        })

    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'STREAM_STOP_ERROR',
                'message': 'Failed to stop stream cleanly',
                'details': str(e)
            }
        }), 500



@app.route('/api/stream/status', methods=['GET'])
def get_stream_status():
    """Get stream status"""
    try:
        uptime_seconds = 0
        if stream_start_time and stream_state == StreamState.RUNNING:
            uptime_seconds = time.time() - stream_start_time

        status = {
            'success': True,
            'state': stream_state.value,
            'uptime_seconds': uptime_seconds,
            'audio_active': audio_streaming,
            'error_message': stream_error_message,
            'pyaudio_available': PYAUDIO_AVAILABLE
        }

        if stream_state in [StreamState.RUNNING, StreamState.STARTING, StreamState.ERROR]:
            status['config'] = {
                'video_device_index': current_config.video_device_index,
                'resolution': list(current_config.resolution),
                'frame_rate': current_config.frame_rate,
                'audio_enabled': current_config.audio_enabled,
                'audio_device_index': current_config.audio_device_index,
                'audio_sample_rate': current_config.audio_sample_rate,
                'audio_channels': current_config.audio_channels
            }

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'STATUS_ERROR',
                'message': 'Failed to get stream status',
                'details': str(e)
            }
        }), 500


# Stream Endpoints

@app.route('/video_feed')
def video_feed():
    """Video MJPEG stream"""
    return Response(gen_video(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    """Serve web UI"""
    response = send_from_directory('static', 'index.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Raspberry Pi Webcam Streamer - Real-time Optimized")
    logger.info("="*60)
    logger.info(f"PyAudio: {'Available' if PYAUDIO_AVAILABLE else 'Not available'}")
    logger.info(f"OpenCV: {cv2.__version__}")
    logger.info("")
    logger.info("Starting server on http://0.0.0.0:8080")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)

    try:
        socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        if audio_input_stream:
            audio_input_stream.stop_stream()
            audio_input_stream.close()
        if audio_stream:
            audio_stream.terminate()
        if video_capture:
            video_capture.release()
