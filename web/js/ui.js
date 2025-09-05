// web/js/ui.js
import { initAudio } from './audio.js';
import { dom } from './dom-elements.js';
import { initSpeechRecognition } from './speech-recognition.js';
import { initCommandPreview } from './commands.js';
import { initAvatarSelection } from './avatars.js';
import { renderMarkdown } from './markdown-renderer.js';

/**
 * @typedef {import('./state.js').AppState} AppState
 * @typedef {import('./api.js').initApi} ApiModule
 */

/**
 * Initializes and returns the UI module, which orchestrates all sub-modules.
 * @param {AppState} state - The central state object.
 * @returns {object} The public interface for the UI module.
 */
export function initUI(state) {
    let api = null;
    const audio = initAudio(state);
    
    const speech = initSpeechRecognition({
        onFinalResult: (text) => { dom.messageInput.value = text; },
        onStatusChange: (isListening) => { dom.micButton.classList.toggle('listening', isListening); }
    });
    initCommandPreview(dom);
    initAvatarSelection(dom, state);

    function _render() {
        const mainElement = document.querySelector('main');
        dom.loginView.style.display = 'none';
        dom.registerView.style.display = 'none';
        dom.mainAppView.style.display = 'none';

        if (state.uiView === 'login' || state.uiView === 'register') {
            mainElement.className = 'auth-mode';
            if (state.uiView === 'login') {
                dom.loginView.style.display = 'flex';
            } else {
                dom.registerView.style.display = 'flex';
            }
        } else {
            mainElement.className = 'app-mode';
            dom.mainAppView.style.display = 'flex';
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

    function _showError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
    }

    function _hideError(element) {
        element.style.display = 'none';
    }

    function _attachListeners() {
        dom.switchToRegisterBtn.addEventListener('click', () => { state.uiView = 'register'; _render(); });
        dom.switchToLoginBtn.addEventListener('click', () => { state.uiView = 'login'; _render(); });
        dom.registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            _hideError(dom.registerError);
            const name = dom.registerNameInput.value.trim();
            const password = dom.registerPasswordInput.value;
            const confirm = dom.registerConfirmPasswordInput.value;
            if (password !== confirm) { _showError(dom.registerError, "Passwords do not match."); return; }
            const result = await api.register(name, state.selectedAvatarStyle, password);
            if (result.success) { alert(result.message); state.uiView = 'login'; _render(); } 
            else { _showError(dom.registerError, result.message); }
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
            } else { _showError(dom.loginError, result.message); }
        });
        dom.logoutButton.addEventListener('click', () => api.logout());
        dom.joinButton.addEventListener('click', () => {
            const roomId = dom.roomIdInput.value.trim();
            if (roomId) api.connectToRoom(roomId);
        });
        dom.leaveButton.addEventListener('click', () => api.disconnect());
        dom.sendButton.addEventListener('click', () => {
            const message = dom.messageInput.value.trim();
            if (message) api.sendMessage('say', { message });
            dom.messageInput.value = '';
            dom.messageInput.focus();
        });
        dom.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); dom.sendButton.click(); }
        });
        if (speech) {
            dom.micButton.addEventListener('mousedown', speech.startListening);
            dom.micButton.addEventListener('mouseup', speech.stopListening);
            dom.micButton.addEventListener('touchstart', speech.startListening, { passive: true });
            dom.micButton.addEventListener('touchend', speech.stopListening);
        } else {
            dom.micButton.style.display = 'none';
        }
        dom.resolveButton.addEventListener('click', () => api.sendMessage('submit_turn'));
        dom.startGameButton.addEventListener('click', () => api.sendMessage('start_game'));
        dom.resumeGameButton.addEventListener('click', () => api.sendMessage('resume_game'));
        dom.themeToggle.addEventListener('click', () => {
            const isLight = document.body.classList.toggle('light-theme');
            localStorage.setItem('vdm-theme', isLight ? 'light' : 'dark');
        });
        const resumeAudio = () => {
            if (state.audioContext && state.audioContext.state === 'suspended') { state.audioContext.resume(); }
            document.body.removeEventListener('click', resumeAudio);
        };
        document.body.addEventListener('click', resumeAudio);
    }
    
    const savedTheme = localStorage.getItem('vdm-theme') || 'dark';
    document.body.classList.toggle('light-theme', savedTheme === 'light');
    _attachListeners();
    _render();

    const publicInterface = {
        setApi(apiModule) { api = apiModule; },
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
                
                messageSpan.innerHTML = renderMarkdown(data.content);

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
        loadChatHistory(messages) {
            dom.chatLog.innerHTML = '';
            messages.forEach(msg => { this.logMessage('chat', msg, true); });
            dom.chatLog.scrollTop = dom.chatLog.scrollHeight;
        },
        updateRoomState(room) {
            state.room = room;
            dom.roomName.textContent = room.room_id;
            dom.playerList.innerHTML = '';
            
            Object.values(room.players).forEach(player => {
                const playerLi = document.createElement('li');
                playerLi.className = player.is_active ? 'player-active' : 'player-inactive';
                const avatarImg = document.createElement('img');
                avatarImg.className = 'player-list-avatar';
                avatarImg.src = `https://api.dicebear.com/9.x/${player.avatar_style}/svg?seed=${encodeURIComponent(player.name)}`;
                const nameSpan = document.createElement('span');
                nameSpan.className = 'player-name';
                nameSpan.textContent = player.name;
                if (room.owner_username === player.name) { nameSpan.textContent += ' 👑'; }
                const turnIndicator = document.createElement('span');
                turnIndicator.className = 'turn-indicator';
                if (room.current_turn_actions && room.current_turn_actions[player.id]) {
                    playerLi.classList.add('action-submitted');
                    turnIndicator.textContent = '✅';
                }
                playerLi.appendChild(avatarImg);
                playerLi.appendChild(nameSpan);
                playerLi.appendChild(turnIndicator);
                dom.playerList.appendChild(playerLi);
            });
            
            const isOwner = (state.playerInfo && room.owner_username === state.playerInfo.name);
            const inLobby = room.game_state === "LOBBY";
            const gmIsProcessing = room.turn_state === "GM_PROCESSING";
            const actionsExist = Object.keys(room.current_turn_actions || {}).length > 0;
            
            dom.gmThinkingIndicator.style.display = gmIsProcessing ? 'flex' : 'none';
            dom.hostControlsContainer.style.display = isOwner ? 'flex' : 'none';
            dom.startGameButton.style.display = inLobby && isOwner ? 'block' : 'none';
            dom.resumeGameButton.style.display = !inLobby && isOwner && room.messages.length > 0 ? 'block' : 'none';
            dom.resolveButton.disabled = !actionsExist || gmIsProcessing;
            dom.messageInput.disabled = gmIsProcessing || inLobby;
            dom.sendButton.disabled = gmIsProcessing || inLobby;
            dom.micButton.disabled = gmIsProcessing || inLobby;
        },
        showRoomView(roomId) { state.isConnected = true; _render(); },
        showConnectionView() { state.isConnected = false; _render(); },
        showLoginView() {
            state.uiView = 'login';
            state.isConnected = false;
            state.playerInfo = null;
            _render();
        },
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
            state.activeStream = { messageElement: msgDiv, contentElement: messageSpan };
            audio.startStream();
        },
        handleChatChunk(content) {
            if (state.activeStream && state.activeStream.contentElement) {
                state.activeStream.contentElement.textContent += content;
                dom.chatLog.scrollTop = dom.chatLog.scrollHeight;
            }
        },
        handleStreamEnd(finalMessage) {
            if (state.activeStream && state.activeStream.messageElement) {
                state.activeStream.messageElement.classList.remove('streaming');
                if (finalMessage) {
                    const finalContentSpan = state.activeStream.contentElement;
                    finalContentSpan.innerHTML = renderMarkdown(finalMessage.content);
                }
            }
            state.activeStream = null;
            audio.endStream();
        },
        playAudioFile(url) { audio.playFullAudioFile(url); }
    };
    return publicInterface;
}