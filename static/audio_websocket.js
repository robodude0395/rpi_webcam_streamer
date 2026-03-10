// WebSocket Audio Streaming
let audioSocket = null;
let audioContext = null;
let audioSource = null;
let nextStartTime = 0;

function startWebSocketAudio() {
    const audioStatus = document.getElementById('audioStatus');

    // Initialize Web Audio API
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 44100
        });
    }

    // Connect to WebSocket
    audioSocket = io('/audio', {
        transports: ['websocket']
    });

    audioSocket.on('connect', () => {
        console.log('Audio WebSocket connected');
        audioStatus.textContent = 'Connected - Playing live audio';
        audioStatus.style.color = '#2e7d32';
    });

    audioSocket.on('audio_data', (data) => {
        try {
            // Convert hex string back to binary
            const hexString = data.data;
            const bytes = new Uint8Array(hexString.length / 2);
            for (let i = 0; i < hexString.length; i += 2) {
                bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);
            }

            // Decode MP3 data
            audioContext.decodeAudioData(bytes.buffer, (audioBuffer) => {
                // Create source and play
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);

                // Schedule playback
                const currentTime = audioContext.currentTime;
                if (nextStartTime < currentTime) {
                    nextStartTime = currentTime;
                }
                source.start(nextStartTime);
                nextStartTime += audioBuffer.duration;
            }, (error) => {
                console.error('Error decoding audio:', error);
            });
        } catch (error) {
            console.error('Error processing audio data:', error);
        }
    });

    audioSocket.on('disconnect', () => {
        console.log('Audio WebSocket disconnected');
        audioStatus.textContent = 'Disconnected';
        audioStatus.style.color = '#c62828';
    });

    audioSocket.on('error', (error) => {
        console.error('Audio WebSocket error:', error);
        audioStatus.textContent = 'Error: ' + error;
        audioStatus.style.color = '#c62828';
    });
}

function stopWebSocketAudio() {
    if (audioSocket) {
        audioSocket.disconnect();
        audioSocket = null;
    }
    nextStartTime = 0;
}
