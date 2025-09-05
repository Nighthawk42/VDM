// web/js/speech-recognition.js

/**
 * Initializes and manages the Web Speech API for speech-to-text functionality.
 * @param {object} options - Configuration for the speech recognition module.
 * @param {(text: string) => void} options.onFinalResult - Callback function when a final transcript is ready.
 * @param {(isListening: boolean) => void} options.onStatusChange - Callback function for listening status updates.
 * @returns {object|null} An object with methods to control speech recognition, or null if not supported.
 */
export function initSpeechRecognition({ onFinalResult, onStatusChange }) {
    // Check for browser support.
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Web Speech API is not supported in this browser.");
        return null;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false; // We want to process speech in single chunks.
    recognition.interimResults = false; // We only care about the final, most accurate result.
    recognition.lang = 'en-US'; // Set language.

    let isListening = false;

    // Event handler for when the API has a final result.
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (onFinalResult) {
            onFinalResult(transcript);
        }
    };

    // Event handler for any errors.
    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        if (isListening) {
            stopListening(); // Ensure we stop if there's an error.
        }
    };

    // Event handler for when listening automatically ends.
    recognition.onend = () => {
        if (isListening) {
            stopListening();
        }
    };

    /**
     * Starts listening for speech.
     */
    function startListening() {
        if (isListening) return;
        try {
            recognition.start();
            isListening = true;
            if (onStatusChange) onStatusChange(true);
        } catch (e) {
            console.error("Could not start speech recognition:", e);
        }
    }

    /**
     * Manually stops listening for speech.
     */
    function stopListening() {
        if (!isListening) return;
        recognition.stop();
        isListening = false;
        if (onStatusChange) onStatusChange(false);
    }

    return {
        startListening,
        stopListening,
    };
}