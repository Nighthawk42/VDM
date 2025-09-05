// web/js/audio.js

/**
 * @typedef {import('./state.js').AppState} AppState
 */

const SAMPLE_RATE = 24000; // Kokoro's native sample rate

/**
 * Initializes and returns the Audio module.
 * This module manages all audio playback, including streaming chunks.
 * @param {AppState} state - The central state object.
 * @returns {object} The Audio module with methods for audio control.
 */
export function initAudio(state) {
    let currentFullAudio = null; // For non-streaming audio files
    let streamSourceNode = null; // For streaming audio: stores the current AudioBufferSourceNode
    let streamStartTime = 0;    // When the current stream segment started playing
    let streamOffset = 0;       // How much of the current segment has played
    let bufferPromise = Promise.resolve(); // Chain promises for sequential playback

    /**
     * Resumes the AudioContext if it's suspended.
     * This needs to be called after a user gesture.
     */
    function _resumeAudioContext() {
        if (state.audioContext && state.audioContext.state === 'suspended') {
            state.audioContext.resume().then(() => {
                console.log("AudioContext resumed successfully.");
            }).catch(e => console.error("Error resuming AudioContext:", e));
        }
    }

    /**
     * Plays a single AudioBuffer, chaining it to the promise queue.
     * @param {AudioBuffer} buffer - The audio buffer to play.
     */
    function _playAudioBuffer(buffer) {
        // Chain this playback onto the existing promise queue
        bufferPromise = bufferPromise.then(() => new Promise(resolve => {
            if (!state.audioContext) {
                console.error("AudioContext not available.");
                state.isPlayingAudio = false;
                return resolve();
            }

            // Resume context if needed before playing
            _resumeAudioContext();

            streamSourceNode = state.audioContext.createBufferSource();
            streamSourceNode.buffer = buffer;
            streamSourceNode.connect(state.audioContext.destination);

            streamSourceNode.onended = () => {
                // When this buffer finishes, resolve the promise for the next chunk
                streamSourceNode = null;
                resolve();
            };

            streamSourceNode.start(0); // Play immediately
        })).catch(e => {
            console.error("Error playing audio buffer:", e);
            state.isPlayingAudio = false;
            // Ensure the promise chain continues even if one fails
            return Promise.resolve(); 
        });
    }

    /**
     * Processes the audio queue and plays chunks if not already playing.
     */
    function _processAudioQueue() {
        if (!state.isPlayingAudio && state.audioQueue.length > 0) {
            state.isPlayingAudio = true;
            _playNextQueuedChunk();
        }
    }

    /**
     * Plays the next chunk from the audio queue.
     * This function calls itself recursively until the queue is empty.
     */
    function _playNextQueuedChunk() {
        if (state.audioQueue.length > 0 && state.audioContext) {
            const rawChunk = state.audioQueue.shift(); // Get the next raw chunk (ArrayBuffer)
            
            // Create an AudioBuffer from the raw float32 PCM data
            // The server sends float32, which can be directly loaded into an AudioBuffer.
            const audioBuffer = state.audioContext.createBuffer(
                1, // mono
                rawChunk.byteLength / Float32Array.BYTES_PER_ELEMENT, // length in samples
                SAMPLE_RATE // sample rate
            );
            
            // Copy the raw float32 data into the AudioBuffer
            const channelData = audioBuffer.getChannelData(0);
            new Float32Array(rawChunk).forEach((value, index) => {
                channelData[index] = value;
            });
            
            _playAudioBuffer(audioBuffer); // Play this chunk
            
            // After the current buffer finishes, play the next one
            bufferPromise.finally(() => {
                // If there are more chunks, continue playing
                if (state.audioQueue.length > 0) {
                    _playNextQueuedChunk();
                } else {
                    state.isPlayingAudio = false;
                    console.log("Audio stream finished.");
                }
            });

        } else {
            state.isPlayingAudio = false;
        }
    }


    const audioModule = {
        /**
         * Clears any active audio and prepares for a new stream.
         */
        startStream() {
            if (currentFullAudio) {
                currentFullAudio.pause();
                currentFullAudio = null;
            }
            if (streamSourceNode) {
                streamSourceNode.stop();
                streamSourceNode = null;
            }
            state.audioQueue = [];
            state.isPlayingAudio = false;
            bufferPromise = Promise.resolve(); // Reset the promise chain
        },

        /**
         * Adds an audio chunk to the queue and triggers playback if needed.
         * @param {ArrayBuffer} chunk - A raw ArrayBuffer of float32 PCM audio data.
         */
        queueAndPlay(chunk) {
            state.audioQueue.push(chunk);
            _processAudioQueue();
        },

        /**
         * Signals the end of the current audio stream.
         * Any remaining queued chunks will still play out.
         */
        endStream() {
            // No explicit action needed here, _processAudioQueue handles depletion.
            // We just ensure the `isPlayingAudio` flag is managed correctly.
            if (state.audioQueue.length === 0) {
                state.isPlayingAudio = false;
            }
        },

        /**
         * Plays a full audio file from a URL (for non-streaming fallback or RVC).
         * @param {string} url - The URL of the audio file.
         */
        playFullAudioFile(url) {
            this.startStream(); // Clear any existing stream or audio
            if (url) {
                currentFullAudio = new Audio(url);
                _resumeAudioContext(); // Ensure context is active before playing
                currentFullAudio.play().catch(e => console.warn("Audio autoplay was blocked or failed for URL:", url, e));
            }
        },

        /**
         * Stops any currently playing audio.
         */
        stopAudio() {
            if (currentFullAudio) {
                currentFullAudio.pause();
                currentFullAudio = null;
            }
            if (streamSourceNode) {
                streamSourceNode.stop();
                streamSourceNode = null;
            }
            state.audioQueue = [];
            state.isPlayingAudio = false;
            bufferPromise = Promise.resolve();
        }
    };

    return audioModule;
}