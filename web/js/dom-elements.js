// web/js/dom-elements.js

/**
 * A centralized cache of all DOM elements used by the UI.
 * This object is queried once and then exported for use by other modules.
 */
export const dom = {
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

    // Chat & Input
    chatLog: document.getElementById('chat-log'),
    messageInput: document.getElementById('message-input'),
    sendButton: document.getElementById('send-button'),
    resolveButton: document.getElementById('resolve-button'),
    gmThinkingIndicator: document.getElementById('gm-thinking-indicator'),
    commandPreview: document.getElementById('command-preview'),
    micButton: document.getElementById('mic-button'),
    themeToggle: document.getElementById('theme-toggle'),
};