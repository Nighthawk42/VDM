// web/js/commands.js

/**
 * @typedef {import('./dom-elements.js').dom} DOM_Elements
 */

// Define the available slash commands and their descriptions.
const COMMANDS = {
    "/roll": "[dice] - Rolls dice (e.g., 2d6+3). Defaults to 1d20.",
    "/ooc": "[message] - Sends an out-of-character message.",
    "/remember": "[fact] - Saves a fact to the GM's long-term memory.",
    "/save": "- Saves the current game session.",
    "/next": "- Submits the current turn actions to the GM."
};

/**
 * Updates the command preview UI based on the user's input.
 * @param {DOM_Elements} dom - The centralized DOM elements object.
 */
function updateCommandPreview(dom) {
    const text = dom.messageInput.value;
    if (text.startsWith('/')) {
        const [typedCmd] = text.split(' ');
        let html = '<h4>Commands</h4><ul>';
        for (const [cmd, desc] of Object.entries(COMMANDS)) {
            // Show commands that start with what the user has typed
            if (cmd.startsWith(typedCmd)) {
                html += `<li><strong>${cmd}</strong>: ${desc}</li>`;
            }
        }
        html += '</ul>';
        dom.commandPreview.innerHTML = html;
        dom.commandPreview.style.display = 'block';
    } else {
        dom.commandPreview.style.display = 'none';
    }
}

/**
 * Initializes the command preview functionality.
 * @param {DOM_Elements} dom - The centralized DOM elements object.
 */
export function initCommandPreview(dom) {
    // Attach event listener to the message input to update the preview on typing.
    dom.messageInput.addEventListener('input', () => updateCommandPreview(dom));

    // Also attach a listener to the send button to clear the preview after sending.
    dom.sendButton.addEventListener('click', () => {
        // A small delay ensures this runs after the input is cleared.
        setTimeout(() => updateCommandPreview(dom), 0);
    });
}