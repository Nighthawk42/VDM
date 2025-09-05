// web/js/state.js

/**
 * @typedef {object} PlayerInfo - Information about the currently logged-in player.
 * @property {string} name - The player's name.
 * @property {string} avatar_style - The selected DiceBear avatar style.
 * @property {string} token - The current session token.
 */

/**
 * @typedef {object} AppState - The central state object for the entire application.
 * @property {string} clientId - A unique ID for this browser session.
 * @property {PlayerInfo | null} playerInfo - Data for the logged-in player, or null if logged out.
 * @property {any | null} room - The full room state object received from the server.
 * @property {boolean} isConnected - True if the WebSocket is currently connected.
 * @property {string} uiView - The current view of the application (e.g., 'login', 'register', 'chat').
 * @property {any | null} activeStream - Holds data related to the current active stream, if any.
 * @property {string} selectedAvatarStyle - The avatar style selected during registration.
 * @property {AudioContext | null} audioContext - The browser's audio context for streaming playback.
 * @property {ArrayBuffer[]} audioQueue - A queue for incoming audio chunks.
 * @property {boolean} isPlayingAudio - A flag to manage the audio playback loop.
 */

/**
 * The single, central state object for the application.
 * @type {AppState}
 */
export const state = {
    clientId: `player-${'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => ((Math.random()*16)|0).toString(16))}`,
    playerInfo: null,
    room: null,
    isConnected: false,
    uiView: 'login', // Default view is now login
    activeStream: null,
    selectedAvatarStyle: 'adventurer', // A default style
    audioContext: null,
    audioQueue: [],
    isPlayingAudio: false,
};

/**
 * Initializes the application state.
 * This function should be called once when the application starts.
 * It loads any persisted user data from localStorage.
 */
export function initState() {
    // Attempt to load player information from localStorage.
    const savedPlayer = localStorage.getItem('vdm-player');
    if (savedPlayer) {
        try {
            const playerData = JSON.parse(savedPlayer);
            // Basic validation to ensure the loaded data has what we need.
            if (playerData.name && playerData.token && playerData.avatar_style) {
                state.playerInfo = playerData;
                // If we have player info, the user is "logged in",
                // so we should show them the connection/chat screen.
                state.uiView = 'chat'; 
            } else {
                // If data is malformed, clear it.
                localStorage.removeItem('vdm-player');
            }
        } catch (e) {
            console.error("Failed to parse saved player data.", e);
            localStorage.removeItem('vdm-player');
        }
    }

    // Initialize the Web Audio API context.
    // It must be created or resumed after a user interaction (like a button click),
    // which we will handle in the UI module.
    try {
        state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        // Start in a suspended state until the user interacts.
        if (state.audioContext.state === 'suspended') {
            console.log("AudioContext is suspended. Will resume on user interaction.");
        }
    } catch (e) {
        console.error("Web Audio API is not supported in this browser.", e);
        // The app can continue without audio streaming.
    }
}