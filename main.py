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
import pyaudio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')


class StreamState(Enum):
    """Stream state enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class StreamConfig:
    """Configuration for video and audio streams"""
    video_device: str = "/dev/video0"
    video_device_index: int = 0
    resolution: tuple = (640, 480)
    frame_rate: int = 30
    audio_enabled: bool = False
    audio_device: Optional[str] = None
    audio_device_index: int = 0
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    audio_chunk_size: int = 1024


# Global stream configuration and state
current_config = StreamConfig()
video_capture: Optional[cv2.VideoCapture] = None
audio_stream: Optional[pyaudio.PyAudio] = None
audio_input_stream = None
stream_state = StreamState.STOPPED
stream_start_time: Optional[float] = None
stream_error_message: Optional[str] = None
monitor_thread: Optional[threading.Thread] = None
monitor_running = False
audio_broadcast_thread: Optional[threading.Thread] = None
audio_broadcast_running = False


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


def gen_video():
    """Generate MJPEG frames from OpenCV VideoCapture"""
    global video_capture

    if not video_capture or not video_capture.isOpened():
        logger.error("No video capture running. Start stream via /api/stream/start first.")
        return

    try:
        while video_capture and video_capture.isOpened():
            ret, frame = video_capture.read()
            if not ret:
                logger.warning("Failed to read frame from video capture")
                break

            # Resize frame if needed
            if frame.shape[1] != current_config.resolution[0] or frame.shape[0] != current_config.resolution[1]:
                frame = cv2.resize(frame, current_config.resolution)

            # Encode frame as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Control frame rate
            time.sleep(1.0 / current_config.frame_rate)

    except Exception as e:
        logger.error(f"Error in video generator: {e}")
    finally:
        logger.info("Video generator stopped")


def monitor_stream_health():
    """
    Monitor stream health and handle failures.
    Runs in a background thread while streaming is active.
    """
    global video_capture, audio_input_stream, stream_state, stream_error_message, monitor_running

    logger.info("Stream health monitor started")

    while monitor_running:
        try:
            # Check video capture health
            if video_capture and not video_capture.isOpened():
                logger.error("Video capture is no longer open")
                stream_state = StreamState.ERROR
                stream_error_message = "Video device became unavailable or disconnected"

                # Stop audio if running
                if audio_input_stream:
                    try:
                        audio_input_stream.stop_stream()
                        audio_input_stream.close()
                    except:
                        pass
                    audio_input_stream = None

                logger.error(stream_error_message)
                break

            # Check audio stream health (if enabled)
            if current_config.audio_enabled and audio_input_stream:
                try:
                    if not audio_input_stream.is_active():
                        logger.warning("Audio stream is no longer active")
                        current_config.audio_enabled = False
                        audio_input_stream = None
                        logger.info("Audio disabled, continuing with video-only stream")
                except Exception as e:
                    logger.warning(f"Audio stream check failed: {e}")
                    current_config.audio_enabled = False
                    audio_input_stream = None

            # Sleep briefly before next check
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error in stream health monitor: {e}")
            time.sleep(1)

    logger.info("Stream health monitor stopped")


def broadcast_audio():
    """Broadcast audio chunks to all connected WebSocket clients"""
    global audio_input_stream, audio_broadcast_running

    logger.info("Audio broadcast thread started")

    while audio_broadcast_running and audio_input_stream:
        try:
            if not audio_input_stream.is_active():
                logger.warning("Audio stream is not active, stopping broadcast")
                break

            # Read audio chunk
            chunk = audio_input_stream.read(current_config.audio_chunk_size, exception_on_overflow=False)

            # Broadcast to all connected clients via WebSocket
            socketio.emit('audio_data', {'data': chunk.hex()}, namespace='/audio')

        except Exception as e:
            logger.error(f"Error broadcasting audio: {e}")
            break

    audio_broadcast_running = False
    logger.info("Audio broadcast thread stopped")


# Socket.IO Event Handlers

@socketio.on('connect', namespace='/audio')
def handle_audio_connect():
    """Handle client connection to audio namespace"""
    logger.info("Audio client connected")


@socketio.on('disconnect', namespace='/audio')
def handle_audio_disconnect():
    """Handle client disconnection from audio namespace"""
    logger.info("Audio client disconnected")


# REST API Endpoints

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """
    Get all available video and audio devices.
    Returns both video and audio devices in one call.
    """
    try:
        video_devices = device_detector.detect_video_devices()
        audio_devices = device_detector.detect_audio_devices()

        return jsonify({
            'success': True,
            'video_devices': video_devices,
            'audio_devices': audio_devices
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


@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """
    Start video and optional audio streams with the provided configuration.

    Expected JSON body:
    {
        "video_device": "/dev/video0",
        "video_device_index": 0,
        "resolution": [640, 480],
        "frame_rate": 30,
        "audio_enabled": false,
        "audio_device": null,
        "audio_device_index": 0,
        "audio_sample_rate": 44100,
        "audio_channels": 2
    }
    """
    global current_config, video_capture, audio_stream, audio_input_stream
    global stream_state, stream_start_time, stream_error_message
    global monitor_running, monitor_thread, audio_broadcast_running, audio_broadcast_thread

    try:
        # Check if stream is already running
        if stream_state == StreamState.RUNNING:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'STREAM_ALREADY_RUNNING',
                    'message': 'Stream is already running',
                    'suggestion': 'Stop the current stream before starting a new one'
                }
            }), 400

        # Parse configuration from request
        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request body must be valid JSON',
                    'details': str(e),
                    'suggestion': 'Provide a valid JSON configuration'
                }
            }), 400

        if data is None:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request body must be JSON',
                    'suggestion': 'Provide a valid JSON configuration'
                }
            }), 400

        # Validate required fields
        if 'video_device_index' not in data and 'video_device' not in data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_VIDEO_DEVICE',
                    'message': 'video_device or video_device_index is required',
                    'suggestion': 'Specify a video device index (e.g., 0) or path (e.g., /dev/video0)'
                }
            }), 400

        # Update configuration
        stream_state = StreamState.STARTING
        current_config.video_device = data.get('video_device', '/dev/video0')
        current_config.video_device_index = data.get('video_device_index', 0)

        # Handle resolution
        resolution = data.get('resolution', [640, 480])
        if isinstance(resolution, list) and len(resolution) == 2:
            current_config.resolution = tuple(resolution)
        else:
            current_config.resolution = (640, 480)

        current_config.frame_rate = data.get('frame_rate', 30)
        current_config.audio_enabled = data.get('audio_enabled', False)
        current_config.audio_device = data.get('audio_device')
        current_config.audio_device_index = data.get('audio_device_index', 0)
        current_config.audio_sample_rate = data.get('audio_sample_rate', 44100)
        current_config.audio_channels = data.get('audio_channels', 2)
        current_config.audio_chunk_size = data.get('audio_chunk_size', 1024)

        # Validate configuration
        if current_config.resolution[0] <= 0 or current_config.resolution[1] <= 0:
            stream_state = StreamState.ERROR
            stream_error_message = 'Invalid resolution: dimensions must be positive'
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_RESOLUTION',
                    'message': stream_error_message,
                    'suggestion': 'Provide positive width and height values'
                }
            }), 400

        if current_config.frame_rate <= 0:
            stream_state = StreamState.ERROR
            stream_error_message = 'Invalid frame rate: must be positive'
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_FRAME_RATE',
                    'message': stream_error_message,
                    'suggestion': 'Provide a positive frame rate value'
                }
            }), 400

        if current_config.audio_enabled and current_config.audio_device_index is None:
            stream_state = StreamState.ERROR
            stream_error_message = 'Audio enabled but no audio device specified'
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_AUDIO_DEVICE',
                    'message': stream_error_message,
                    'suggestion': 'Specify an audio device index or disable audio'
                }
            }), 400

        # Stop any existing streams
        if video_capture:
            video_capture.release()
            video_capture = None

        if audio_input_stream:
            try:
                audio_input_stream.stop_stream()
                audio_input_stream.close()
            except:
                pass
            audio_input_stream = None

        # Start video capture
        try:
            video_capture = cv2.VideoCapture(current_config.video_device_index)

            if not video_capture.isOpened():
                raise Exception(f"Failed to open video device at index {current_config.video_device_index}")

            # Set video properties
            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, current_config.resolution[0])
            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, current_config.resolution[1])
            video_capture.set(cv2.CAP_PROP_FPS, current_config.frame_rate)

            logger.info(f"Started video capture: device {current_config.video_device_index} at {current_config.resolution[0]}x{current_config.resolution[1]}@{current_config.frame_rate}fps")

        except Exception as e:
            stream_state = StreamState.ERROR
            stream_error_message = f"Failed to start video capture: {str(e)}"
            logger.error(stream_error_message)
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VIDEO_START_FAILED',
                    'message': 'Failed to start video stream',
                    'details': str(e),
                    'suggestion': 'Check that the video device exists and is accessible. Verify device index and permissions.'
                }
            }), 500

        # Start audio capture if enabled
        if current_config.audio_enabled:
            try:
                audio_stream = pyaudio.PyAudio()
                audio_input_stream = audio_stream.open(
                    format=pyaudio.paInt16,
                    channels=current_config.audio_channels,
                    rate=current_config.audio_sample_rate,
                    input=True,
                    input_device_index=current_config.audio_device_index,
                    frames_per_buffer=current_config.audio_chunk_size
                )

                logger.info(f"Started audio capture: device {current_config.audio_device_index} at {current_config.audio_sample_rate}Hz, {current_config.audio_channels} channels")

                # Start audio broadcast thread
                audio_broadcast_running = True
                audio_broadcast_thread = threading.Thread(target=broadcast_audio, daemon=True)
                audio_broadcast_thread.start()
                logger.info("Audio WebSocket broadcast enabled")

            except Exception as e:
                # Audio failure is non-fatal - continue with video only
                logger.warning(f"Failed to start audio stream: {e}. Continuing with video-only mode.")
                current_config.audio_enabled = False
                audio_input_stream = None
                if audio_stream:
                    audio_stream.terminate()
                    audio_stream = None

        # Update state
        stream_state = StreamState.RUNNING
        stream_start_time = time.time()
        stream_error_message = None

        # Start health monitoring thread
        monitor_running = True
        monitor_thread = threading.Thread(target=monitor_stream_health, daemon=True)
        monitor_thread.start()
        logger.info("Stream health monitoring enabled")

        return jsonify({
            'success': True,
            'message': 'Stream started successfully',
            'config': {
                'video_device': current_config.video_device,
                'video_device_index': current_config.video_device_index,
                'resolution': list(current_config.resolution),
                'frame_rate': current_config.frame_rate,
                'audio_enabled': current_config.audio_enabled,
                'audio_device': current_config.audio_device,
                'audio_device_index': current_config.audio_device_index
            }
        })

    except Exception as e:
        stream_state = StreamState.ERROR
        stream_error_message = str(e)
        logger.error(f"Error starting stream: {e}")
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
    """
    Stop all active streams (video and audio).
    """
    global video_capture, audio_stream, audio_input_stream
    global stream_state, stream_start_time, stream_error_message
    global monitor_running, monitor_thread, audio_broadcast_running, audio_broadcast_thread

    try:
        # Stop monitoring thread
        if monitor_running:
            monitor_running = False
            if monitor_thread:
                monitor_thread.join(timeout=2)
                monitor_thread = None
            logger.info("Stream health monitoring stopped")

        # Stop audio broadcast thread
        if audio_broadcast_running:
            audio_broadcast_running = False
            if audio_broadcast_thread:
                audio_broadcast_thread.join(timeout=2)
                audio_broadcast_thread = None
            logger.info("Audio broadcast stopped")

        # Stop audio stream
        if audio_input_stream:
            try:
                audio_input_stream.stop_stream()
                audio_input_stream.close()
            except:
                pass
            audio_input_stream = None
            logger.info("Stopped audio stream")

        if audio_stream:
            try:
                audio_stream.terminate()
            except:
                pass
            audio_stream = None

        # Stop video capture
        if video_capture:
            video_capture.release()
            video_capture = None
            logger.info("Stopped video capture")

        # Update state
        stream_state = StreamState.STOPPED
        stream_start_time = None
        stream_error_message = None

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
                'details': str(e),
                'suggestion': 'The stream may have already stopped or encountered an error'
            }
        }), 500


@app.route('/api/stream/status', methods=['GET'])
def get_stream_status():
    """
    Get current stream status including state, configuration, and statistics.
    """
    try:
        # Calculate uptime
        uptime_seconds = 0
        if stream_start_time and stream_state == StreamState.RUNNING:
            uptime_seconds = time.time() - stream_start_time

        # Build status response
        status = {
            'success': True,
            'state': stream_state.value,
            'uptime_seconds': uptime_seconds,
            'audio_active': current_config.audio_enabled and audio_input_stream is not None,
            'error_message': stream_error_message
        }

        # Include configuration if stream is running or in error state
        if stream_state in [StreamState.RUNNING, StreamState.STARTING, StreamState.ERROR]:
            status['config'] = {
                'video_device': current_config.video_device,
                'video_device_index': current_config.video_device_index,
                'resolution': list(current_config.resolution),
                'frame_rate': current_config.frame_rate,
                'audio_enabled': current_config.audio_enabled,
                'audio_device': current_config.audio_device,
                'audio_device_index': current_config.audio_device_index,
                'audio_sample_rate': current_config.audio_sample_rate,
                'audio_channels': current_config.audio_channels
            }

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting stream status: {e}")
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
    """Stream video via MJPEG over HTTP"""
    return Response(gen_video(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    """Serve the main web UI"""
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
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
