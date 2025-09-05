// web/js/ui.js
import { initAudio } from './audio.js';

/**
 * @typedef {import('./state.js').AppState} AppState
 * @typedef {import('./api.js').initApi} ApiModule
 */

/**
 * @typedef {object} AppUI - The public interface of the UI module.
 * @property {(api: ReturnType<ApiModule>) => void} setApi
 * @property {(type: string, data: any) => void} logMessage
 * @property {(room: any) => void} updateRoomState
 * @property {(url: string) => void} playAudioFile
 * @property {() => void} handleStreamStart
 * @property {(content: string) => void} handleChatChunk
 * @property {(chunk: ArrayBuffer) => void} handleAudioChunk
 * @property {(finalMessage: any) => void} handleStreamEnd
 * @property {(roomId: string) => void} showRoomView
 * @property {() => void} showConnectionView
 * @property {() => void} showLoginView
 */

// List of available avatar styles.
const AVATAR_STYLES = [
    "adventurer", "adventurer-neutral", "avataaars", "big-ears", "big-smile", 
    "bottts", "croodles", "fun-emoji", "icons", "identicon", "initials", 
    "lorelei", "micah", "miniavs", "open-peeps", "personas", "pixel-art", "rings"
];

/**
 * Initializes and returns the UI module.
 * @param {AppState} state - The central state object.
 * @returns {AppUI}
 */
export function initUI(state) {
    // A cache for all DOM elements we will interact with.
    const dom = {
        // Auth Forms & Views
        loginView: document.getElementById('login-view'),
        registerView: document.getElementById('register-view'),
        loginForm: document.getElementById('login-form'),
        registerForm: document.getElementById('register-form'),
        loginNameInput: document.getElementById('login-name'),
        loginPasswordInput: document.getElementById('login-password'),
        registerNameInput: document.getElementById('register-name'),
        registerPasswordInput: document.getElementById('register-password'),
        registerConfirmPasswordInput: document.getElementById('register-confirm-password'),
        loginError: document.getElementById('login-error'),
        registerError: document.getElementById('register-error'),
        switchToRegisterBtn: document.getElementById('switch-to-register'),
        switchToLoginBtn: document.getElementById('switch-to-login'),
        
        // Avatar Selection
        avatarSelectionGrid: document.getElementById('avatar-selection-grid'),
        registerAvatarPreview: document.getElementById('register-avatar-preview'),

        // Main App View
        mainAppView: document.getElementById('main-app-view'),
        sidebar: document.querySelector('.sidebar'),
        chatArea: document.querySelector('.chat-area'),

        // Player Info & Connection
        playerIdentity: document.getElementById('player-identity'),
        playerCardAvatar: document.getElementById('player-card-avatar'),
        playerCardName: document.getElementById('player-card-name'),
        logoutButton: document.getElementById('logout-button'),
        connectionForm: document.getElementById('connection-form'),
        roomIdInput: document.getElementById('room-id-input'),
        joinButton: document.getElementById('join-button'),
        
        // In-Room Info
        roomInfo: document.getElementById('room-info'),
        roomName: document.getElementById('room-name'),
        playerList: document.getElementById('player-list'),
        hostControlsContainer: document.getElementById('host-controls-container'),
        startGameButton: document.getElementById('start-game-button'),
        resumeGameButton: document.getElementById('resume-game-button'),
        leaveButton: document.getElementById('leave-button'),

        // Chat
        chatLog: document.getElementById('chat-log'),
        messageInput: document.getElementById('message-input'),
        sendButton: document.getElementById('send-button'),
        resolveButton: document.getElementById('resolve-button'),
        gmThinkingIndicator: document.getElementById('gm-thinking-indicator'),
        themeToggle: document.getElementById('theme-toggle'),
    };

    // Module dependencies, to be set later.
    let api = null;
    const audio = initAudio(state);

    /** Main render function to switch between primary UI views */
    function _render() {
        const mainElement = document.querySelector('main');

        // Hide all view containers initially
        dom.loginView.style.display = 'none';
        dom.registerView.style.display = 'none';
        dom.mainAppView.style.display = 'none';

        // Set a class on the <main> element to control the overall layout via CSS
        if (state.uiView === 'login' || state.uiView === 'register') {
            mainElement.className = 'auth-mode';
            // Show the correct auth form
            if (state.uiView === 'login') {
                dom.loginView.style.display = 'flex';
            } else {
                dom.registerView.style.display = 'flex';
            }
        } else { // 'chat' or other authenticated views
            mainElement.className = 'app-mode';
            dom.mainAppView.style.display = 'flex';

            // This logic to show/hide sections within the app remains the same
            if (state.playerInfo) {
                dom.playerIdentity.style.display = 'flex';
                dom.playerCardName.textContent = state.playerInfo.name;
                dom.playerCardAvatar.src = `https://api.dicebear.com/9.x/${state.playerInfo.avatar_style}/svg?seed=${encodeURIComponent(state.playerInfo.name)}`;
            } else {
                dom.playerIdentity.style.display = 'none';
            }
            
            if (state.isConnected) {
                dom.connectionForm.style.display = 'none';
                dom.roomInfo.style.display = 'flex';
            } else {
                dom.connectionForm.style.display = 'flex';
                dom.roomInfo.style.display = 'none';
            }
        }
    }

    function _updateAvatarSelectionUI() {
        const name = dom.registerNameInput.value.trim() || 'player';
        dom.registerAvatarPreview.src = `https://api.dicebear.com/9.x/${state.selectedAvatarStyle}/svg?seed=${encodeURIComponent(name)}`;
        dom.avatarSelectionGrid.querySelectorAll('.avatar-option').forEach(opt => {
            opt.classList.toggle('selected', opt.dataset.style === state.selectedAvatarStyle);
        });
    }
    
    function _populateAvatarGrid() {
        const grid = dom.avatarSelectionGrid;
        grid.innerHTML = '';
        AVATAR_STYLES.forEach(style => {
            const option = document.createElement('div');
            option.className = 'avatar-option';
            option.dataset.style = style;
            const img = document.createElement('img');
            img.src = `https://api.dicebear.com/9.x/${style}/svg`;
            img.alt = style;
            option.appendChild(img);
            grid.appendChild(option);
        });
        _updateAvatarSelectionUI();
    }

    function _showError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
    }

    function _hideError(element) {
        element.style.display = 'none';
    }

    /** Attach all event listeners for the application */
    function _attachListeners() {
        // --- Auth Listeners ---
        dom.switchToRegisterBtn.addEventListener('click', () => { state.uiView = 'register'; _render(); });
        dom.switchToLoginBtn.addEventListener('click', () => { state.uiView = 'login'; _render(); });

        dom.registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            _hideError(dom.registerError);
            const name = dom.registerNameInput.value.trim();
            const password = dom.registerPasswordInput.value;
            const confirm = dom.registerConfirmPasswordInput.value;

            if (password !== confirm) {
                _showError(dom.registerError, "Passwords do not match.");
                return;
            }

            const result = await api.register(name, state.selectedAvatarStyle, password);
            if (result.success) {
                alert(result.message);
                state.uiView = 'login';
                _render();
            } else {
                _showError(dom.registerError, result.message);
            }
        });

        dom.loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            _hideError(dom.loginError);
            const name = dom.loginNameInput.value.trim();
            const password = dom.loginPasswordInput.value;
            const result = await api.login(name, password);

            if (result.success) {
                state.playerInfo = result.data;
                localStorage.setItem('vdm-player', JSON.stringify(result.data));
                state.uiView = 'chat';
                _render();
            } else {
                _showError(dom.loginError, result.message);
            }
        });

        dom.logoutButton.addEventListener('click', () => api.logout());

        // --- Avatar Selection ---
        dom.registerNameInput.addEventListener('input', () => _updateAvatarSelectionUI());
        dom.avatarSelectionGrid.addEventListener('click', (e) => {
            const option = e.target.closest('.avatar-option');
            if (option && option.dataset.style) {
                state.selectedAvatarStyle = option.dataset.style;
                _updateAvatarSelectionUI();
            }
        });

        // --- Connection Listeners ---
        dom.joinButton.addEventListener('click', () => {
            const roomId = dom.roomIdInput.value.trim();
            if (roomId) api.connectToRoom(roomId);
        });
        dom.leaveButton.addEventListener('click', () => api.disconnect());

        // --- Chat Listeners ---
        dom.sendButton.addEventListener('click', () => {
            const message = dom.messageInput.value.trim();
            if (message) api.sendMessage('say', { message });
            dom.messageInput.value = '';
            dom.messageInput.focus();
        });
        dom.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                dom.sendButton.click();
            }
        });
        dom.resolveButton.addEventListener('click', () => api.sendMessage('submit_turn'));
        
        // --- Host Listeners ---
        dom.startGameButton.addEventListener('click', () => api.sendMessage('start_game'));
        dom.resumeGameButton.addEventListener('click', () => api.sendMessage('resume_game'));

        // --- Misc Listeners ---
        dom.themeToggle.addEventListener('click', () => {
            const isLight = document.body.classList.toggle('light-theme');
            localStorage.setItem('vdm-theme', isLight ? 'light' : 'dark');
        });

        // Resume AudioContext on any user interaction
        const resumeAudio = () => {
            if (state.audioContext && state.audioContext.state === 'suspended') {
                state.audioContext.resume();
            }
            document.body.removeEventListener('click', resumeAudio);
        };
        document.body.addEventListener('click', resumeAudio);
    }
    
    // --- Initialize ---
    const savedTheme = localStorage.getItem('vdm-theme') || 'dark';
    document.body.classList.toggle('light-theme', savedTheme === 'light');
    _populateAvatarGrid();
    _attachListeners();
    _render(); // Set the initial view based on loaded state

    // --- Public UI Methods ---
    /** @type {AppUI} */
    const publicInterface = {
        setApi(apiModule) {
            api = apiModule;
        },

        logMessage(type, data, isBatch = false) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('msg', type);

            if (type === 'system') {
                msgDiv.textContent = data.message;
            } else if (type === 'chat') {
                msgDiv.classList.add(data.author_id === 'gm' ? 'gm' : 'player');
                if (data.is_ooc) msgDiv.classList.add('ooc');

                const avatarImg = document.createElement('img');
                avatarImg.className = 'msg-avatar';
                
                const player = state.room?.players[data.author_id];
                const avatarStyle = player ? player.avatar_style : 'bottts';
                const avatarSeed = data.author_id === 'gm' ? 'GM' : encodeURIComponent(data.author_name);
                avatarImg.src = `https://api.dicebear.com/9.x/${data.author_id === 'gm' ? 'bottts' : avatarStyle}/svg?seed=${avatarSeed}`;

                const contentDiv = document.createElement('div');
                contentDiv.className = 'msg-content';

                const authorSpan = document.createElement('span');
                authorSpan.className = 'author';
                authorSpan.textContent = data.author_name;

                const messageSpan = document.createElement('span');
                let contentHTML = data.content.replace(/`([^`]+)`/g, '<code>$1</code>');
                contentHTML = contentHTML.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
                messageSpan.innerHTML = contentHTML;

                contentDiv.appendChild(authorSpan);
                contentDiv.appendChild(messageSpan);
                msgDiv.appendChild(avatarImg);
                msgDiv.appendChild(contentDiv);
            }
            
            dom.chatLog.appendChild(msgDiv);
            if (!isBatch) {
                dom.chatLog.scrollTop = dom.chatLog.scrollHeight;
            }
        },

        updateRoomState(room) {
            state.room = room;
            dom.roomName.textContent = room.room_id;
            dom.playerList.innerHTML = ''; // Clear previous list
            
            Object.values(room.players).forEach(player => {
                const playerLi = document.createElement('li');
                playerLi.className = player.is_active ? 'player-active' : 'player-inactive';

                const avatarImg = document.createElement('img');
                avatarImg.className = 'player-list-avatar';
                avatarImg.src = `https://api.dicebear.com/9.x/${player.avatar_style}/svg?seed=${encodeURIComponent(player.name)}`;

                const nameSpan = document.createElement('span');
                nameSpan.className = 'player-name';
                nameSpan.textContent = player.name;
                if (room.host_player_id === player.id) {
                    nameSpan.textContent += ' 👑'; // Host indicator
                }
                
                const hpSpan = document.createElement('span');
                hpSpan.className = 'player-hp';
                if (player.sheet) {
                    hpSpan.textContent = `${player.sheet.hp}/${player.sheet.max_hp} HP`;
                }

                playerLi.appendChild(avatarImg);
                playerLi.appendChild(nameSpan);
                playerLi.appendChild(hpSpan);
                dom.playerList.appendChild(playerLi);
            });
            
            // Update UI based on game state
            const isHost = (room.host_player_id === state.clientId);
            const inLobby = room.game_state === "LOBBY";
            const gmIsProcessing = room.turn_state === "GM_PROCESSING";
            const actionsExist = Object.keys(room.current_turn_actions || {}).length > 0;
            
            dom.gmThinkingIndicator.style.display = gmIsProcessing ? 'flex' : 'none';
            dom.hostControlsContainer.style.display = isHost ? 'flex' : 'none';
            dom.startGameButton.style.display = inLobby && isHost ? 'block' : 'none';
            dom.resumeGameButton.style.display = !inLobby && isHost && room.messages.length > 0 ? 'block' : 'none';
            dom.resolveButton.disabled = !actionsExist || gmIsProcessing;
            dom.messageInput.disabled = gmIsProcessing || inLobby;
            dom.sendButton.disabled = gmIsProcessing || inLobby;
        },

        // --- View Changers ---
        showRoomView(roomId) {
            state.isConnected = true;
            state.room = { room_id: roomId, players: {} }; // temporary state
            _render();
        },
        showConnectionView() {
            state.isConnected = false;
            _render();
        },
        showLoginView() {
            state.uiView = 'login';
            _render();
        },

        // --- Streaming Handlers ---
        handleStreamStart() {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('msg', 'chat', 'gm', 'streaming');
            const avatarImg = document.createElement('img');
            avatarImg.src = `https://api.dicebear.com/9.x/bottts/svg?seed=GM`;
            avatarImg.className = 'msg-avatar';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'msg-content';
            const authorSpan = document.createElement('span');
            authorSpan.className = 'author';
            authorSpan.textContent = 'GM';
            const messageSpan = document.createElement('span');
            
            contentDiv.appendChild(authorSpan);
            contentDiv.appendChild(messageSpan);
            msgDiv.appendChild(avatarImg);
            msgDiv.appendChild(contentDiv);
            dom.chatLog.appendChild(msgDiv);

            state.activeStream = {
                messageElement: msgDiv,
                contentElement: messageSpan,
            };

            audio.startStream();
        },

        handleChatChunk(content) {
            if (state.activeStream && state.activeStream.contentElement) {
                state.activeStream.contentElement.textContent += content;
                dom.chatLog.scrollTop = dom.chatLog.scrollHeight;
            }
        },

        handleAudioChunk(chunk) {
            audio.queueAndPlay(chunk);
        },

        handleStreamEnd(finalMessage) {
            if (state.activeStream && state.activeStream.messageElement) {
                state.activeStream.messageElement.classList.remove('streaming');
            }
            state.activeStream = null;
            audio.endStream();
        },

        playAudioFile(url) {
            audio.playFullAudioFile(url);
        }
    };

    return publicInterface;
}