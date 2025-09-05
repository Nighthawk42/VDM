// web/js/api.js

/**
 * @typedef {import('./state.js').AppState} AppState
 * @typedef {import('./ui.js').AppUI} AppUI
 */

/**
 * Initializes and returns the API module.
 * This module handles all communication with the backend server.
 * @param {AppState} state - The central state object.
 * @param {AppUI} ui - The UI module instance.
 * @returns {object} The API module with methods for server interaction.
 */
export function initApi(state, ui) {
    let ws = null; // Private WebSocket instance

    /**
     * Handles incoming WebSocket messages and updates the state/UI accordingly.
     * @param {MessageEvent} event - The WebSocket message event.
     */
    function handleWsMessage(event) {
        try {
            const msg = JSON.parse(event.data);

            switch (msg.kind) {
                case 'system':
                    ui.logMessage('system', msg.payload);
                    break;
                case 'state_update':
                    ui.updateRoomState(msg.payload);
                    break;
                case 'chat': // Non-streamed complete message
                    ui.logMessage('chat', msg.payload);
                    break;
                // NEW: Handle the batch of historical messages upon joining.
                case 'chat_history':
                    ui.loadChatHistory(msg.payload.messages);
                    break;
                case 'audio': // Non-streamed complete audio file
                    ui.playAudioFile(msg.payload.url);
                    break;
                
                // --- Streaming Handlers ---
                case 'stream_start':
                    ui.handleStreamStart();
                    break;
                case 'chat_chunk':
                    ui.handleChatChunk(msg.payload.content);
                    break;

                case 'audio_chunk': {
                    // Chunks arrive as base64, so we must decode them.
                    const binaryString = atob(msg.payload.chunk);
                    const len = binaryString.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    // The audio module (via UI) will handle the decoded chunk
                    ui.handleAudioChunk(bytes.buffer);
                    break;
                }
                
                case 'stream_end':
                    ui.handleStreamEnd(msg.payload.final_message);
                    break;
            }
        } catch (error) {
            console.error("Error processing WebSocket message:", error);
        }
    }

    const api = {
        /**
         * Attempts to register a new user.
         * @param {string} name 
         * @param {string} avatar_style 
         * @param {string} password 
         * @returns {Promise<{success: boolean, message: string}>}
         */
        async register(name, avatar_style, password) {
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, avatar_style, password }),
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || 'Registration failed.');
                }
                return { success: true, message: data.message };
            } catch (error) {
                return { success: false, message: error.message };
            }
        },

        /**
         * Attempts to log in a user.
         * @param {string} name 
         * @param {string} password 
         * @returns {Promise<{success: boolean, data?: any, message?: string}>}
         */
        async login(name, password) {
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, password }),
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || 'Login failed.');
                }
                return { success: true, data: data };
            } catch (error) {
                return { success: false, message: error.message };
            }
        },

        /**
         * Connects to the WebSocket server for a given room.
         * @param {string} roomId 
         */
        connectToRoom(roomId) {
            if (ws || !state.playerInfo) return;

            const { token } = state.playerInfo;
            const proto = window.location.protocol === "https:" ? "wss" : "ws";
            const wsURL = `${proto}://${window.location.host}/ws/${roomId}/${state.clientId}/${token}`;
            
            ws = new WebSocket(wsURL);

            ws.onopen = () => {
                state.isConnected = true;
                ui.showRoomView(roomId);
                console.log(`WebSocket connected to room: ${roomId}`);
            };

            ws.onmessage = handleWsMessage;

            ws.onclose = (event) => {
                if(event.code === 4001) {
                    // Specific auth error from the server
                    alert("Session is invalid, please log in again.");
                    this.logout(); // The logout function will handle cleanup
                } else {
                    ui.logMessage('system', { message: 'Disconnected from the room.' });
                }
                this.disconnect();
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                ui.logMessage('system', { message: 'A connection error occurred.' });
                this.disconnect();
            };
        },

        /**
         * Disconnects from the WebSocket server and cleans up the state.
         */
        disconnect() {
            if (ws) {
                ws.close();
                ws = null;
            }
            state.isConnected = false;
            state.room = null;
            ui.showConnectionView();
        },

        /**
         * Logs the user out by clearing their saved data and disconnecting.
         */
        logout() {
            localStorage.removeItem('vdm-player');
            state.playerInfo = null;
            this.disconnect(); // This will also update the UI
            ui.showLoginView();
        },

        /**
         * Sends a message over the WebSocket.
         * @param {string} kind - The message kind (e.g., 'say', 'submit_turn').
         * @param {object} payload - The message payload.
         */
        sendMessage(kind, payload = {}) {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                console.warn("Attempted to send message while disconnected.");
                return;
            }
            ws.send(JSON.stringify({ kind, payload }));
        }
    };

    return api;
}