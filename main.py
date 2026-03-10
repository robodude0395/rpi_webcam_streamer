import subprocess
import time
import logging
import threading
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from typing import Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import device_detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    """Configuration for video and audio streams"""
    video_device: str = "/dev/video0"
    video_format: str = "yuyv422"
    resolution: tuple = (640, 480)
    frame_rate: int = 30
    audio_enabled: bool = False
    audio_device: Optional[str] = None
    audio_format: str = "s16le"
    audio_sample_rate: int = 44100
    audio_channels: int = 1

    def to_ffmpeg_video_args(self) -> List[str]:
        """Generate FFmpeg arguments for video capture"""
        return [
            "ffmpeg",
            "-f", "v4l2",
            "-input_format", self.video_format,
            "-framerate", str(self.frame_rate),
            "-video_size", f"{self.resolution[0]}x{self.resolution[1]}",
            "-i", self.video_device,
            "-f", "mjpeg",
            "pipe:1"
        ]

    def to_ffmpeg_audio_args(self) -> List[str]:
        """Generate FFmpeg arguments for audio capture - raw PCM for WebSocket streaming"""
        if not self.audio_enabled or not self.audio_device:
            return []
        return [
            "ffmpeg",
            "-f", "alsa",
            "-i", self.audio_device,
            "-ar", str(self.audio_sample_rate),
            "-ac", str(self.audio_channels),
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "pipe:1"
        ]


# Global stream configuration and processes
current_config = StreamConfig()
video_process: Optional[subprocess.Popen] = None
audio_process: Optional[subprocess.Popen] = None
stream_state = StreamState.STOPPED
stream_start_time: Optional[float] = None
stream_error_message: Optional[str] = None
monitor_thread: Optional[threading.Thread] = None
monitor_running = False
audio_broadcast_thread: Optional[threading.Thread] = None
audio_broadcast_running = False
stream_error_message: Optional[str] = None
monitor_thread: Optional[threading.Thread] = None
monitor_running = False


def gen_video():
    """Generate MJPEG frames from FFmpeg stdout"""
    global video_process

    # Use the existing video process started by /api/stream/start
    if not video_process:
        logger.error("No video process running. Start stream via /api/stream/start first.")
        return

    try:
        while video_process and video_process.poll() is None:
            # MJPEG frames are separated by 0xFFD8 (start) and 0xFFD9 (end)
            data = b''
            while True:
                byte = video_process.stdout.read(1)
                if not byte:
                    break
                data += byte
                if data[-2:] == b'\xff\xd9':  # JPEG end marker
                    break
            if data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
            else:
                break
    except Exception as e:
        logger.error(f"Error in video generator: {e}")


def monitor_stream_health():
    """
    Monitor FFmpeg process health and handle failures.
    Runs in a background thread while streaming is active.

    Implements requirements 6.1, 6.2, 6.4:
    - Detects when video device becomes unavailable
    - Detects when audio device becomes unavailable
    - Captures FFmpeg error output for user presentation
    """
    global video_process, audio_process, stream_state, stream_error_message, monitor_running

    logger.info("Stream health monitor started")

    while monitor_running:
        try:
            # Check video process health
            if video_process and video_process.poll() is not None:
                # Video process has terminated
                exit_code = video_process.returncode
                stderr_output = video_process.stderr.read().decode('utf-8', errors='ignore') if video_process.stderr else ""

                logger.error(f"Video process terminated unexpectedly (exit code: {exit_code})")
                logger.error(f"FFmpeg stderr: {stderr_output}")

                # Update state
                stream_state = StreamState.ERROR
                stream_error_message = f"Video device became unavailable or FFmpeg failed (exit code: {exit_code})"

                if stderr_output:
                    # Extract meaningful error from FFmpeg output
                    if "No such file or directory" in stderr_output or "Cannot open" in stderr_output:
                        stream_error_message = "Video device not found or inaccessible. Please check device connection."
                    elif "Permission denied" in stderr_output:
                        stream_error_message = "Permission denied accessing video device. Check device permissions."
                    elif "Invalid argument" in stderr_output or "not supported" in stderr_output:
                        stream_error_message = "Video format or settings not supported by device."
                    else:
                        # Include first line of error for debugging
                        error_lines = [line for line in stderr_output.split('\n') if line.strip()]
                        if error_lines:
                            stream_error_message += f" Error: {error_lines[-1][:100]}"

                # Stop audio process if running
                if audio_process:
                    audio_process.terminate()
                    audio_process.wait()
                    audio_process = None

                logger.error(stream_error_message)
                break

            # Check audio process health (if enabled)
            if audio_process and audio_process.poll() is not None:
                # Audio process has terminated
                exit_code = audio_process.returncode
                stderr_output = audio_process.stderr.read().decode('utf-8', errors='ignore') if audio_process.stderr else ""

                logger.warning(f"Audio process terminated unexpectedly (exit code: {exit_code})")
                logger.warning(f"FFmpeg stderr: {stderr_output}")

                # Audio failure is non-fatal - disable audio and continue video
                current_config.audio_enabled = False
                audio_process = None

                logger.info("Audio disabled, continuing with video-only stream")

            # Sleep briefly before next check
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error in stream health monitor: {e}")
            time.sleep(1)

    logger.info("Stream health monitor stopped")


def gen_audio():
    """Generate audio chunks from FFmpeg stdout"""
    global audio_process

    # Use the existing audio process started by /api/stream/start
    if not current_config.audio_enabled or not audio_process:
        logger.error("No audio process running or audio not enabled.")
        return

    try:
        while audio_process and audio_process.poll() is None:
            chunk = audio_process.stdout.read(8192)  # Smaller chunks for lower latency
            if not chunk:
                break
            yield chunk
    except Exception as e:
        logger.error(f"Error in audio generator: {e}")


def broadcast_audio():
    """Broadcast audio chunks to all connected WebSocket clients"""
    global audio_process, audio_broadcast_running

    logger.info("Audio broadcast thread started")

    while audio_broadcast_running and audio_process:
        try:
            if audio_process.poll() is not None:
                logger.warning("Audio process terminated, stopping broadcast")
                break

            chunk = audio_process.stdout.read(4096)
            if not chunk:
                break

            # Broadcast to all connected clients
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
    logger.info(f"Audio client connected")


@socketio.on('disconnect', namespace='/audio')
def handle_audio_disconnect():
    """Handle client disconnection from audio namespace"""
    logger.info(f"Audio client disconnected")


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
        "video_format": "yuyv422",
        "resolution": [640, 480],
        "frame_rate": 30,
        "audio_enabled": false,
        "audio_device": null,
        "audio_format": "s16le",
        "audio_sample_rate": 44100,
        "audio_channels": 1
    }
    """
    global current_config, video_process, audio_process, stream_state, stream_start_time, stream_error_message

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
        if 'video_device' not in data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_VIDEO_DEVICE',
                    'message': 'video_device is required',
                    'suggestion': 'Specify a video device path (e.g., /dev/video0)'
                }
            }), 400

        # Update configuration
        stream_state = StreamState.STARTING
        current_config.video_device = data.get('video_device')
        current_config.video_format = data.get('video_format', 'yuyv422')

        # Handle resolution
        resolution = data.get('resolution', [640, 480])
        if isinstance(resolution, list) and len(resolution) == 2:
            current_config.resolution = tuple(resolution)
        else:
            current_config.resolution = (640, 480)

        current_config.frame_rate = data.get('frame_rate', 30)
        current_config.audio_enabled = data.get('audio_enabled', False)
        current_config.audio_device = data.get('audio_device')
        current_config.audio_format = data.get('audio_format', 's16le')
        current_config.audio_sample_rate = data.get('audio_sample_rate', 44100)
        current_config.audio_channels = data.get('audio_channels', 1)

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

        if current_config.audio_enabled and not current_config.audio_device:
            stream_state = StreamState.ERROR
            stream_error_message = 'Audio enabled but no audio device specified'
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_AUDIO_DEVICE',
                    'message': stream_error_message,
                    'suggestion': 'Specify an audio device or disable audio'
                }
            }), 400

        # Stop any existing processes
        if video_process:
            video_process.terminate()
            video_process.wait()
            video_process = None

        if audio_process:
            audio_process.terminate()
            audio_process.wait()
            audio_process = None

        # Start video process
        try:
            video_process = subprocess.Popen(
                current_config.to_ffmpeg_video_args(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            logger.info(f"Started video stream: {current_config.video_device} at {current_config.resolution[0]}x{current_config.resolution[1]}@{current_config.frame_rate}fps")
        except FileNotFoundError as e:
            stream_state = StreamState.ERROR
            stream_error_message = "FFmpeg not found. Please install FFmpeg."
            logger.error(stream_error_message)
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FFMPEG_NOT_FOUND',
                    'message': stream_error_message,
                    'details': str(e),
                    'suggestion': 'Install FFmpeg using your package manager (e.g., apt install ffmpeg)'
                }
            }), 500
        except Exception as e:
            stream_state = StreamState.ERROR
            stream_error_message = f"Failed to start video stream: {str(e)}"
            logger.error(stream_error_message)
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VIDEO_START_FAILED',
                    'message': 'Failed to start video stream',
                    'details': str(e),
                    'suggestion': 'Check that the video device exists and is accessible. Verify device path and permissions.'
                }
            }), 500

        # Start audio process if enabled
        if current_config.audio_enabled:
            try:
                audio_process = subprocess.Popen(
                    current_config.to_ffmpeg_audio_args(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=10**8
                )
                logger.info(f"Started audio stream: {current_config.audio_device} at {current_config.audio_sample_rate}Hz")

                # Start audio broadcast thread
                global audio_broadcast_running, audio_broadcast_thread
                audio_broadcast_running = True
                audio_broadcast_thread = threading.Thread(target=broadcast_audio, daemon=True)
                audio_broadcast_thread.start()
                logger.info("Audio WebSocket broadcast enabled")
            except Exception as e:
                # Audio failure is non-fatal - continue with video only
                logger.warning(f"Failed to start audio stream: {e}. Continuing with video-only mode.")
                current_config.audio_enabled = False
                audio_process = None

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
                'video_format': current_config.video_format,
                'resolution': list(current_config.resolution),
                'frame_rate': current_config.frame_rate,
                'audio_enabled': current_config.audio_enabled,
                'audio_device': current_config.audio_device
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
    global video_process, audio_process, stream_state, stream_start_time, stream_error_message, monitor_running, monitor_thread, audio_broadcast_running, audio_broadcast_thread

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

        # Stop video process
        if video_process:
            video_process.terminate()
            video_process.wait(timeout=5)
            video_process = None
            logger.info("Stopped video stream")

        # Stop audio process
        if audio_process:
            audio_process.terminate()
            audio_process.wait(timeout=5)
            audio_process = None
            logger.info("Stopped audio stream")

        # Update state
        stream_state = StreamState.STOPPED
        stream_start_time = None
        stream_error_message = None

        return jsonify({
            'success': True,
            'message': 'Stream stopped successfully'
        })

    except subprocess.TimeoutExpired:
        logger.error("Timeout while stopping stream processes")
        # Force kill if timeout
        if video_process:
            video_process.kill()
            video_process = None
        if audio_process:
            audio_process.kill()
            audio_process = None

        stream_state = StreamState.STOPPED
        stream_start_time = None

        return jsonify({
            'success': True,
            'message': 'Stream stopped (forced termination)'
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
            'audio_active': current_config.audio_enabled and audio_process is not None,
            'error_message': stream_error_message
        }

        # Include configuration if stream is running or in error state
        if stream_state in [StreamState.RUNNING, StreamState.STARTING, StreamState.ERROR]:
            status['config'] = {
                'video_device': current_config.video_device,
                'video_format': current_config.video_format,
                'resolution': list(current_config.resolution),
                'frame_rate': current_config.frame_rate,
                'audio_enabled': current_config.audio_enabled,
                'audio_device': current_config.audio_device,
                'audio_format': current_config.audio_format,
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
    return Response(gen_video(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/audio_feed')
def audio_feed():
    """Stream audio if enabled"""
    if not current_config.audio_enabled:
        return Response("Audio not enabled", status=400)

    def generate():
        for chunk in gen_audio():
            yield chunk

    return Response(generate(), mimetype='audio/mpeg', headers={
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })


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
