/**
 * Real-time Audio Streaming Client
 * Optimized for low latency using Web Audio API
 */

let audioSocket = null;
let audioContext = null;
let nextPlayTime = 0;
let packetsReceived = 0;
let isAudioStreaming = false;

// Audio configuration - must match server
const SAMPLE_RATE = 16000;
const CHANNELS = 1;

function startRealtimeAudio() {
    if (isAudioStreaming) {
        console.log('Audio already streaming');
        return;
    }

    const audioStatus = document.getElementById('audioStatus');

    try {
        // Create audio context with low latency settings
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: SAMPLE_RATE,
            latencyHint: 'interactive'  // Minimize latency
        });

        nextPlayTime = audioContext.currentTime;
        packetsReceived = 0;
        isAudioStreaming = true;

        // Connect to WebSocket
        audioSocket = io('/audio', {
            transports: ['websocket'],
            upgrade: false  // Don't upgrade to avoid delays
        });

        audioSocket.on('connect', () => {
            console.log('Audio WebSocket connected');
            audioStatus.textContent = 'Connected - Starting audio...';
            audioStatus.style.color = '#ff9800';

            // Request audio stream
            audioSocket.emit('start_audio');
        });

        audioSocket.on('audio_chunk', (hexData) => {
            if (!isAudioStreaming || !audioContext) return;

            try {
                packetsReceived++;

                // Convert hex string to Int16Array
                const bytes = new Uint8Array(hexData.length / 2);
                for (let i = 0; i < bytes.length; i++) {
                    bytes[i] = parseInt(hexData.substr(i * 2, 2), 16);
                }

                const int16Array = new Int16Array(bytes.buffer);

                // Convert to Float32Array for Web Audio API
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {
                    float32Array[i] = int16Array[i] / 32768.0;  // Normalize
                }

                // Create audio buffer
                const audioBuffer = audioContext.createBuffer(
                    CHANNELS,
                    float32Array.length,
                    SAMPLE_RATE
                );
                audioBuffer.getChannelData(0).set(float32Array);

                // Create and schedule buffer source
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);

                // Schedule playback
                if (nextPlayTime < audioContext.currentTime) {
                    nextPlayTime = audioContext.currentTime;
                }

                source.start(nextPlayTime);
                nextPlayTime += audioBuffer.duration;

                // Update status
                if (packetsReceived === 1) {
                    audioStatus.textContent = 'Streaming (real-time)';
                    audioStatus.style.color = '#2e7d32';
                }

                // Log buffer status periodically
                if (packetsReceived % 100 === 0) {
                    const bufferMs = Math.round((nextPlayTime - audioContext.currentTime) * 1000);
                    console.log(`Audio buffer: ${bufferMs}ms, packets: ${packetsReceived}`);
                }

            } catch (error) {
                console.error('Error processing audio chunk:', error);
            }
        });

        audioSocket.on('disconnect', () => {
            console.log('Audio WebSocket disconnected');
            audioStatus.textContent = 'Disconnected';
            audioStatus.style.color = '#c62828';
            isAudioStreaming = false;
        });

        audioSocket.on('error', (error) => {
            console.error('Audio WebSocket error:', error);
            audioStatus.textContent = 'Error: ' + (error.message || error);
            audioStatus.style.color = '#c62828';
        });

    } catch (error) {
        console.error('Error starting audio:', error);
        audioStatus.textContent = 'Error: ' + error.message;
        audioStatus.style.color = '#c62828';
        isAudioStreaming = false;
    }
}

function stopRealtimeAudio() {
    if (!isAudioStreaming) return;

    const audioStatus = document.getElementById('audioStatus');

    isAudioStreaming = false;

    if (audioSocket) {
        audioSocket.emit('stop_audio');
        audioSocket.disconnect();
        audioSocket = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    nextPlayTime = 0;
    packetsReceived = 0;

    audioStatus.textContent = 'Stopped';
    audioStatus.style.color = '#757575';

    console.log('Audio streaming stopped');
}

// Export functions for use in HTML
window.startRealtimeAudio = startRealtimeAudio;
window.stopRealtimeAudio = stopRealtimeAudio;
