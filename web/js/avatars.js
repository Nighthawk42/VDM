// web/js/avatars.js

/**
 * @typedef {import('./dom-elements.js').dom} DOM_Elements
 * @typedef {import('./state.js').AppState} AppState
 */

// A list of all available DiceBear avatar styles for the registration form.
const AVATAR_STYLES = [
    "adventurer", "adventurer-neutral", "avataaars", "big-ears", "big-smile",    
    "bottts", "croodles", "fun-emoji", "icons", "identicon", "initials",    
    "lorelei", "micah", "miniavs", "open-peeps", "personas", "pixel-art", "rings"
];

/**
 * Updates the avatar preview image and highlights the currently selected style.
 * @param {DOM_Elements} dom The centralized DOM elements object.
 * @param {AppState} state The central state object.
 */
function updateAvatarSelectionUI(dom, state) {
    const name = dom.registerNameInput.value.trim() || 'player';
    dom.registerAvatarPreview.src = `https://api.dicebear.com/9.x/${state.selectedAvatarStyle}/svg?seed=${encodeURIComponent(name)}`;
    dom.avatarSelectionGrid.querySelectorAll('.avatar-option').forEach(opt => {
        opt.classList.toggle('selected', opt.dataset.style === state.selectedAvatarStyle);
    });
}

/**
 * Generates the grid of clickable avatar style options.
 * @param {DOM_Elements} dom The centralized DOM elements object.
 * @param {AppState} state The central state object.
 */
function populateAvatarGrid(dom, state) {
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
    updateAvatarSelectionUI(dom, state);
}

/**
 * Initializes all functionality for the avatar selection component.
 * @param {DOM_Elements} dom The centralized DOM elements object.
 * @param {AppState} state The central state object.
 */
export function initAvatarSelection(dom, state) {
    // Generate the avatar grid when the module is initialized.
    populateAvatarGrid(dom, state);

    // Attach event listeners for dynamic updates.
    dom.registerNameInput.addEventListener('input', () => updateAvatarSelectionUI(dom, state));
    dom.avatarSelectionGrid.addEventListener('click', (e) => {
        const option = e.target.closest('.avatar-option');
        if (option && option.dataset.style) {
            state.selectedAvatarStyle = option.dataset.style;
            updateAvatarSelectionUI(dom, state);
        }
    });
}